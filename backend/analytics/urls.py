"""Analytics API routes."""

from django.urls import path

from analytics.views import (
    AnalyticsBreakdownView,
    AnalyticsDistributionView,
    AnalyticsOutliersView,
    AnalyticsSummaryView,
    AnalyticsTeamView,
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
    path(
        "analytics/team/<int:manager_id>",
        AnalyticsTeamView.as_view(),
        name="analytics-team",
    ),
    path(
        "analytics/outliers",
        AnalyticsOutliersView.as_view(),
        name="analytics-outliers",
    ),
]
