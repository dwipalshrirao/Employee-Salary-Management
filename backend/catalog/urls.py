"""Catalog API routes."""

from django.urls import path

from catalog.views import LookupsView

urlpatterns = [
    path("lookups", LookupsView.as_view(), name="lookups"),
]
