from django.db.models import Count
from rest_framework import generics, status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.models import Album, Photo
from api.serializers import (
    AlbumSerializer,
    LoginSerializer,
    PhotoSerializer,
    PhotoUploadSerializer,
    RegisterSerializer,
    UserSerializer,
)


class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)
        return Response(
            {"token": token.key, "user": UserSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)
        return Response({"token": token.key, "user": UserSerializer(user).data})


class AlbumListCreateView(generics.ListCreateAPIView):
    serializer_class = AlbumSerializer

    def get_queryset(self):
        return (
            Album.objects.filter(owner=self.request.user)
            .annotate(photo_count=Count("photos"))
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class PhotoListView(generics.ListAPIView):
    serializer_class = PhotoSerializer

    def get_queryset(self):
        queryset = Photo.objects.filter(owner=self.request.user).select_related("album", "metadata")
        album_id = self.request.query_params.get("album")
        if album_id:
            queryset = queryset.filter(album_id=album_id)
        return queryset


class PhotoDetailView(generics.RetrieveAPIView):
    serializer_class = PhotoSerializer

    def get_queryset(self):
        return Photo.objects.filter(owner=self.request.user).select_related("album", "metadata")


class PhotoUploadView(generics.CreateAPIView):
    serializer_class = PhotoUploadSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        photo = serializer.save()
        return Response(PhotoSerializer(photo).data, status=status.HTTP_201_CREATED)


class DashboardView(APIView):
    def get(self, request):
        albums = (
            Album.objects.filter(owner=request.user)
            .annotate(photo_count=Count("photos"))
            .order_by("-created_at")
        )
        photos = Photo.objects.filter(owner=request.user).select_related("album", "metadata")[:24]
        return Response(
            {
                "albums": AlbumSerializer(albums, many=True).data,
                "recent_photos": PhotoSerializer(photos, many=True).data,
                "stats": {
                    "album_count": albums.count(),
                    "photo_count": Photo.objects.filter(owner=request.user).count(),
                    "processing_count": Photo.objects.filter(
                        owner=request.user,
                        upload_status=Photo.UploadStatus.PROCESSING,
                    ).count(),
                },
            }
        )
