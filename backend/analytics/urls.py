"""Analytics API routes."""

from django.urls import path

from analytics.views import (
    AnalyticsBreakdownView,
    AnalyticsDistributionView,
    AnalyticsSummaryView,
)

urlpatterns = [
    path(
        "analytics/summary",
        AnalyticsSummaryView.as_view(),
        name="analytics-summary",
    ),
    path(
        "analytics/breakdown",
        AnalyticsBreakdownView.as_view(),
        name="analytics-breakdown",
    ),
    path(
        "analytics/distribution",
        AnalyticsDistributionView.as_view(),
        name="analytics-distribution",
    ),
]
