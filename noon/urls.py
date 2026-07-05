"""Noon URL routes. Namespaced 'noon' - reverse as noon:<name>."""
from django.urls import path

from noon import views

app_name = "noon"

urlpatterns = [
    path("", views.report, name="report"),
    path("health/", views.health, name="health"),
]
