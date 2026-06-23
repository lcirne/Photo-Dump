from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers

from api.models import Album, Photo, PhotoMetadata
from api.services.media import get_media_storage
from api.services.uploads import UploadValidationError, create_photo_upload

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "date_joined")


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        if User.objects.filter(username=attrs["username"]).exists():
            raise serializers.ValidationError({"username": "Username is already taken."})
        if User.objects.filter(email=attrs["email"]).exists():
            raise serializers.ValidationError({"email": "Email is already registered."})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        user = authenticate(username=attrs["username"], password=attrs["password"])
        if not user:
            raise serializers.ValidationError("Invalid username or password.")
        attrs["user"] = user
        return attrs


class AlbumSerializer(serializers.ModelSerializer):
    photo_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Album
        fields = ("id", "title", "description", "visibility", "created_at", "photo_count")
        read_only_fields = ("id", "created_at", "photo_count")


class PhotoMetadataSerializer(serializers.ModelSerializer):
    class Meta:
        model = PhotoMetadata
        fields = (
            "camera_model",
            "lens",
            "iso",
            "shutter_speed",
            "aperture",
            "focal_length",
            "captured_at",
        )


class PhotoSerializer(serializers.ModelSerializer):
    metadata = PhotoMetadataSerializer(read_only=True)
    original_url = serializers.SerializerMethodField()
    thumbnail_url = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    album_title = serializers.CharField(source="album.title", read_only=True)

    class Meta:
        model = Photo
        fields = (
            "id",
            "album",
            "album_title",
            "checksum",
            "original_filename",
            "mime_type",
            "width",
            "height",
            "upload_status",
            "created_at",
            "original_url",
            "thumbnail_url",
            "preview_url",
            "metadata",
        )
        read_only_fields = fields

    def get_original_url(self, obj):
        return get_media_storage().generate_signed_url(obj.storage_key)

    def get_thumbnail_url(self, obj):
        if not obj.thumbnail_key:
            return None
        return get_media_storage().generate_signed_url(obj.thumbnail_key)

    def get_preview_url(self, obj):
        if not obj.preview_key:
            return None
        return get_media_storage().generate_signed_url(obj.preview_key)


class PhotoUploadSerializer(serializers.Serializer):
    file = serializers.FileField()
    album = serializers.IntegerField(required=False)

    def create(self, validated_data):
        try:
            return create_photo_upload(
                owner=self.context["request"].user,
                uploaded_file=validated_data["file"],
                album_id=validated_data.get("album"),
            )
        except UploadValidationError as exc:
            raise serializers.ValidationError(str(exc)) from exc
