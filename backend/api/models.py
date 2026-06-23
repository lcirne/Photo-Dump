from django.conf import settings
from django.db import models


class Album(models.Model):
    class Visibility(models.TextChoices):
        PRIVATE = "private", "Private"
        UNLISTED = "unlisted", "Unlisted"
        PUBLIC = "public", "Public"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="albums",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    visibility = models.CharField(
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.PRIVATE,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class Photo(models.Model):
    class UploadStatus(models.TextChoices):
        PROCESSING = "processing", "Processing"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="photos",
        on_delete=models.CASCADE,
    )
    album = models.ForeignKey(
        Album,
        related_name="photos",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    storage_key = models.CharField(max_length=512, unique=True)
    thumbnail_key = models.CharField(max_length=512, blank=True)
    preview_key = models.CharField(max_length=512, blank=True)
    checksum = models.CharField(max_length=64, db_index=True)
    original_filename = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=120)
    width = models.PositiveIntegerField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    upload_status = models.CharField(
        max_length=16,
        choices=UploadStatus.choices,
        default=UploadStatus.PROCESSING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["owner", "checksum"],
                name="unique_photo_checksum_per_owner",
            )
        ]

    def __str__(self):
        return self.original_filename


class PhotoMetadata(models.Model):
    photo = models.OneToOneField(
        Photo,
        related_name="metadata",
        on_delete=models.CASCADE,
    )
    camera_model = models.CharField(max_length=255, blank=True)
    lens = models.CharField(max_length=255, blank=True)
    iso = models.PositiveIntegerField(null=True, blank=True)
    shutter_speed = models.CharField(max_length=64, blank=True)
    aperture = models.CharField(max_length=64, blank=True)
    focal_length = models.CharField(max_length=64, blank=True)
    captured_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Metadata for photo {self.photo_id}"

# Create your models here.
