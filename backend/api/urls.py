from django.urls import path

from api.views import (
    AlbumListCreateView,
    DashboardView,
    LoginView,
    PhotoDetailView,
    PhotoListView,
    PhotoUploadView,
    RegisterView,
)

urlpatterns = [
    path("auth/register", RegisterView.as_view(), name="register"),
    path("auth/login", LoginView.as_view(), name="login"),
    path("albums", AlbumListCreateView.as_view(), name="albums"),
    path("photos", PhotoListView.as_view(), name="photos"),
    path("photos/upload", PhotoUploadView.as_view(), name="photo-upload"),
    path("photos/<int:pk>", PhotoDetailView.as_view(), name="photo-detail"),
    path("dashboard", DashboardView.as_view(), name="dashboard"),
]
