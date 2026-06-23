import mimetypes
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile, File
from django.core.files.storage import FileSystemStorage


@dataclass(frozen=True)
class StoredMedia:
    storage_key: str
    mime_type: str


class MediaStorageError(RuntimeError):
    pass


class BaseMediaStorage:
    def upload_file(self, file_obj, key: str, content_type: str) -> StoredMedia:
        raise NotImplementedError

    def upload_bytes(self, data: bytes, key: str, content_type: str) -> StoredMedia:
        raise NotImplementedError

    def open_file(self, key: str):
        raise NotImplementedError

    def generate_signed_url(self, key: str, expires_in: int = 3600) -> str:
        raise NotImplementedError

    def delete_file(self, key: str) -> None:
        raise NotImplementedError


class LocalMediaStorage(BaseMediaStorage):
    def __init__(self):
        self.storage = FileSystemStorage(
            location=settings.MEDIA_ROOT,
            base_url=settings.MEDIA_URL,
        )

    def upload_file(self, file_obj, key: str, content_type: str) -> StoredMedia:
        saved_key = self.storage.save(key, file_obj)
        return StoredMedia(storage_key=saved_key, mime_type=content_type)

    def upload_bytes(self, data: bytes, key: str, content_type: str) -> StoredMedia:
        saved_key = self.storage.save(key, ContentFile(data))
        return StoredMedia(storage_key=saved_key, mime_type=content_type)

    def open_file(self, key: str):
        return self.storage.open(key, "rb")

    def generate_signed_url(self, key: str, expires_in: int = 3600) -> str:
        return self.storage.url(key)

    def delete_file(self, key: str) -> None:
        if self.storage.exists(key):
            self.storage.delete(key)


class SupabaseMediaStorage(BaseMediaStorage):
    def __init__(self):
        if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE_KEY:
            raise MediaStorageError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are required.")
        self.base_url = settings.SUPABASE_URL.rstrip("/")
        self.bucket = settings.SUPABASE_STORAGE_BUCKET
        self.headers = {
            "apikey": settings.SUPABASE_SERVICE_ROLE_KEY,
            "Authorization": f"Bearer {settings.SUPABASE_SERVICE_ROLE_KEY}",
        }

    def upload_file(self, file_obj, key: str, content_type: str) -> StoredMedia:
        return self._upload(file_obj.read(), key, content_type)

    def upload_bytes(self, data: bytes, key: str, content_type: str) -> StoredMedia:
        return self._upload(data, key, content_type)

    def _upload(self, data: bytes, key: str, content_type: str) -> StoredMedia:
        import requests

        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{key}"
        response = requests.post(
            url,
            headers={**self.headers, "Content-Type": content_type, "x-upsert": "false"},
            data=data,
            timeout=60,
        )
        if response.status_code >= 400:
            raise MediaStorageError(response.text)
        return StoredMedia(storage_key=key, mime_type=content_type)

    def open_file(self, key: str):
        import requests

        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{key}"
        response = requests.get(url, headers=self.headers, timeout=60)
        if response.status_code >= 400:
            raise MediaStorageError(response.text)
        return ContentFile(response.content)

    def generate_signed_url(self, key: str, expires_in: int = 3600) -> str:
        import requests

        url = f"{self.base_url}/storage/v1/object/sign/{self.bucket}/{key}"
        response = requests.post(
            url,
            headers={**self.headers, "Content-Type": "application/json"},
            json={"expiresIn": expires_in},
            timeout=30,
        )
        if response.status_code >= 400:
            raise MediaStorageError(response.text)
        signed_path = response.json().get("signedURL")
        if not signed_path:
            raise MediaStorageError("Supabase did not return a signed URL.")
        if signed_path.startswith("http"):
            return signed_path
        return f"{self.base_url}/storage/v1{signed_path}"

    def delete_file(self, key: str) -> None:
        import requests

        url = f"{self.base_url}/storage/v1/object/{self.bucket}/{key}"
        response = requests.delete(url, headers=self.headers, timeout=30)
        if response.status_code >= 400:
            raise MediaStorageError(response.text)


def get_media_storage() -> BaseMediaStorage:
    if settings.MEDIA_STORAGE_BACKEND == "supabase":
        return SupabaseMediaStorage()
    return LocalMediaStorage()


def build_storage_key(user_id: int, filename: str, variant: str = "originals") -> str:
    suffix = Path(filename).suffix.lower()
    if not suffix:
        suffix = mimetypes.guess_extension("image/jpeg") or ".jpg"
    return os.path.join(str(user_id), variant, f"{uuid.uuid4().hex}{suffix}")


def as_django_file(file_obj):
    if isinstance(file_obj, File):
        return file_obj
    return File(file_obj)
