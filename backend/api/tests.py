from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.models import Album, Photo

User = get_user_model()


class PhaseOneApiTests(APITestCase):
    def test_register_returns_token_and_user(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "nikan",
                "email": "nikan@example.com",
                "password": "strong-password",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("token", response.data)
        self.assertEqual(response.data["user"]["username"], "nikan")

    def test_album_create_and_list_is_scoped_to_user(self):
        self._authenticate()

        create_response = self.client.post(
            reverse("albums"),
            {"title": "SD Card Import", "description": "First batch"},
            format="json",
        )
        list_response = self.client.get(reverse("albums"))

        self.assertEqual(create_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)
        self.assertEqual(list_response.data[0]["title"], "SD Card Import")

    def test_upload_creates_photo_record_immediately(self):
        user = self._authenticate()
        album = Album.objects.create(owner=user, title="Camera Roll")

        response = self.client.post(
            reverse("photo-upload"),
            {"album": album.id, "file": self._image_file()},
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Photo.objects.count(), 1)
        photo = Photo.objects.get()
        self.assertEqual(photo.owner, user)
        self.assertEqual(photo.album, album)
        self.assertEqual(photo.upload_status, Photo.UploadStatus.PROCESSING)
        self.assertEqual(len(photo.checksum), 64)

    def test_duplicate_upload_is_rejected_for_same_user(self):
        self._authenticate()

        first = self.client.post(
            reverse("photo-upload"),
            {"file": self._image_file()},
            format="multipart",
        )
        second = self.client.post(
            reverse("photo-upload"),
            {"file": self._image_file()},
            format="multipart",
        )

        self.assertEqual(first.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(Photo.objects.count(), 1)

    def test_dashboard_returns_phase_one_summary(self):
        self._authenticate()

        response = self.client.get(reverse("dashboard"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("albums", response.data)
        self.assertIn("recent_photos", response.data)
        self.assertIn("stats", response.data)

    def _authenticate(self):
        response = self.client.post(
            reverse("register"),
            {
                "username": "phaseone",
                "email": "phaseone@example.com",
                "password": "strong-password",
            },
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {response.data['token']}")
        return User.objects.get(username="phaseone")

    def _image_file(self):
        return SimpleUploadedFile(
            "camera.jpg",
            (
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00"
                b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
                b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
                b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342"
                b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00"
                b"\xff\xc4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00"
                b"\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
                b"\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xd2\xcf \xff\xd9"
            ),
            content_type="image/jpeg",
        )
