from django.contrib import admin

from .models import Album, Photo, PhotoMetadata


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "visibility", "created_at")
    search_fields = ("title", "owner__username", "owner__email")
    list_filter = ("visibility", "created_at")


@admin.register(Photo)
class PhotoAdmin(admin.ModelAdmin):
    list_display = (
        "original_filename",
        "owner",
        "album",
        "upload_status",
        "mime_type",
        "created_at",
    )
    search_fields = ("original_filename", "owner__username", "checksum")
    list_filter = ("upload_status", "mime_type", "created_at")
    readonly_fields = ("checksum", "storage_key", "thumbnail_key", "preview_key")


@admin.register(PhotoMetadata)
class PhotoMetadataAdmin(admin.ModelAdmin):
    list_display = ("photo", "camera_model", "lens", "captured_at")
    search_fields = ("photo__original_filename", "camera_model", "lens")

# Register your models here.
