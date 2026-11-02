from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="kaloum24_preview_home"),
    path("healthz", views.health, name="kaloum24_preview_health"),
    path("healthz/", views.health),
    path("robots.txt", views.robots),
]
