"""Catalog API routes."""

from django.urls import path

from catalog.views import CurrencyRateDetailView, CurrencyRateListView, LookupsView

urlpatterns = [
    path("lookups", LookupsView.as_view(), name="lookups"),
    path(
        "currency-rates",
        CurrencyRateListView.as_view(),
        name="currency-rates-list",
    ),
    path(
        "currency-rates/<str:code>",
        CurrencyRateDetailView.as_view(),
        name="currency-rates-detail",
    ),
]
