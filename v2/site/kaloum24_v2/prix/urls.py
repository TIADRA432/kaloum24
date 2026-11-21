from django.urls import path

from . import views

urlpatterns = [
    path("", views.accueil, name="prix"),
    path("<int:pk>/", views.produit, name="prix_produit"),
]
