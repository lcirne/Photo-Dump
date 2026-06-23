import hashlib

from django.db import transaction

from api.models import Album, Photo

from .media import build_storage_key, get_media_storage

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}


class UploadValidationError(ValueError):
    pass


def create_photo_upload(*, owner, uploaded_file, album_id=None) -> Photo:
    content_type = uploaded_file.content_type or ""
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise UploadValidationError("Unsupported image type.")

    checksum = _sha256(uploaded_file)
    album = None
    if album_id:
        album = Album.objects.get(id=album_id, owner=owner)

    existing = Photo.objects.filter(owner=owner, checksum=checksum).first()
    if existing:
        raise UploadValidationError("This file has already been uploaded.")

    storage = get_media_storage()
    key = build_storage_key(owner.id, uploaded_file.name)

    with transaction.atomic():
        stored = storage.upload_file(uploaded_file, key, content_type)
        photo = Photo.objects.create(
            owner=owner,
            album=album,
            storage_key=stored.storage_key,
            checksum=checksum,
            original_filename=uploaded_file.name,
            mime_type=stored.mime_type,
        )

    enqueue_media_processing(photo.id)
    return photo


def enqueue_media_processing(photo_id: int) -> None:
    try:
        from api.tasks import process_photo_upload

        process_photo_upload.delay(photo_id)
    except Exception:
        # Local development can run without Redis/Celery; records still exist immediately.
        return


def _sha256(uploaded_file) -> str:
    hasher = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        hasher.update(chunk)
    uploaded_file.seek(0)
    return hasher.hexdigest()
