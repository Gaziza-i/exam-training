"""URL configuration for the «Умный тренажёр для ЕГЭ» backend."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("exam.urls")),
]
