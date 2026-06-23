from datetime import datetime
from fractions import Fraction
from io import BytesIO

from django.utils import timezone
from PIL import ExifTags, Image

from api.models import Photo, PhotoMetadata
from api.services.media import build_storage_key, get_media_storage

try:
    from celery import shared_task
except ImportError:
    class _Task:
        def __init__(self, fn):
            self.fn = fn

        def __call__(self, *args, **kwargs):
            return self.fn(*args, **kwargs)

        def delay(self, *args, **kwargs):
            return None

    def shared_task(fn):
        return _Task(fn)


@shared_task
def process_photo_upload(photo_id: int) -> None:
    photo = Photo.objects.get(id=photo_id)
    storage = get_media_storage()

    try:
        with storage.open_file(photo.storage_key) as image_file:
            with Image.open(image_file) as image:
                image.load()
                photo.width, photo.height = image.size
                _write_variant(storage, photo, image, size=(480, 480), variant="thumbnails")
                _write_variant(storage, photo, image, size=(1600, 1600), variant="previews")
                _upsert_metadata(photo, image)

        photo.upload_status = Photo.UploadStatus.READY
        photo.save(update_fields=["width", "height", "thumbnail_key", "preview_key", "upload_status"])
    except Exception:
        photo.upload_status = Photo.UploadStatus.FAILED
        photo.save(update_fields=["upload_status"])
        raise


def _write_variant(storage, photo: Photo, image: Image.Image, *, size, variant: str) -> None:
    output = image.copy()
    output.thumbnail(size)
    if output.mode not in ("RGB", "L"):
        output = output.convert("RGB")

    buffer = BytesIO()
    output.save(buffer, format="JPEG", quality=85, optimize=True)
    key = build_storage_key(photo.owner_id, f"{photo.id}.jpg", variant=variant)
    storage.upload_bytes(buffer.getvalue(), key, "image/jpeg")

    if variant == "thumbnails":
        photo.thumbnail_key = key
    elif variant == "previews":
        photo.preview_key = key


def _upsert_metadata(photo: Photo, image: Image.Image) -> None:
    exif = image.getexif()
    readable = {
        ExifTags.TAGS.get(tag, tag): value
        for tag, value in exif.items()
    }
    captured_at = _parse_exif_datetime(readable.get("DateTimeOriginal"))

    PhotoMetadata.objects.update_or_create(
        photo=photo,
        defaults={
            "camera_model": readable.get("Model", "") or "",
            "lens": readable.get("LensModel", "") or "",
            "iso": readable.get("ISOSpeedRatings"),
            "shutter_speed": _format_fraction(readable.get("ExposureTime")),
            "aperture": _format_aperture(readable.get("FNumber")),
            "focal_length": _format_focal_length(readable.get("FocalLength")),
            "captured_at": captured_at,
        },
    )


def _format_fraction(value) -> str:
    if value in (None, ""):
        return ""
    try:
        fraction = Fraction(value).limit_denominator()
        if fraction.numerator < fraction.denominator:
            return f"{fraction.numerator}/{fraction.denominator}"
        return str(round(float(fraction), 3))
    except (TypeError, ValueError, ZeroDivisionError):
        return str(value)


def _format_aperture(value) -> str:
    if value in (None, ""):
        return ""
    try:
        return f"f/{round(float(value), 1)}"
    except (TypeError, ValueError):
        return str(value)


def _format_focal_length(value) -> str:
    if value in (None, ""):
        return ""
    try:
        return f"{round(float(value), 1)}mm"
    except (TypeError, ValueError):
        return str(value)


def _parse_exif_datetime(value):
    if not value:
        return None
    try:
        parsed = datetime.strptime(value, "%Y:%m:%d %H:%M:%S")
        return timezone.make_aware(parsed, timezone.get_current_timezone())
    except (TypeError, ValueError):
        return None
