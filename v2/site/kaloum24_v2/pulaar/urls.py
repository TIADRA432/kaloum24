from django.urls import path

from . import views

app_name = "pulaar"

urlpatterns = [
    path("", views.accueil, name="accueil"),
    path("terme/<slug:slug>/", views.terme, name="terme"),
    path("domaine/<slug:slug>/", views.domaine, name="domaine"),
    path("proposer/", views.proposer, name="proposer"),
]
