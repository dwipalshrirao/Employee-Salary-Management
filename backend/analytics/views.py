"""Analytics API views."""

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from analytics.serializers import (
    BreakdownQuerySerializer,
    BreakdownResponseSerializer,
    DistributionQuerySerializer,
    DistributionResponseSerializer,
    SummaryQuerySerializer,
    SummaryResponseSerializer,
)
from analytics.services import get_breakdown, get_distribution, get_summary


class AnalyticsSummaryView(APIView):
    """Return organisation-wide pay totals and components."""

    @extend_schema(
        operation_id="analytics-summary",
        tags=["analytics"],
        parameters=[SummaryQuerySerializer],
        responses={200: SummaryResponseSerializer},
    )
    def get(self, request, format=None):
        query = SummaryQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        result = get_summary(**query.validated_data)
        return Response(SummaryResponseSerializer(result).data)


class AnalyticsBreakdownView(APIView):
    """Return headcount and pay statistics grouped by one dimension."""

    @extend_schema(
        operation_id="analytics-breakdown",
        tags=["analytics"],
        parameters=[BreakdownQuerySerializer],
        responses={200: BreakdownResponseSerializer},
    )
    def get(self, request, format=None):
        query = BreakdownQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        result = get_breakdown(**query.validated_data)
        return Response(BreakdownResponseSerializer(result).data)


class AnalyticsDistributionView(APIView):
    """Return salary-band counts across the selected population."""

    @extend_schema(
        operation_id="analytics-distribution",
        tags=["analytics"],
        parameters=[DistributionQuerySerializer],
        responses={200: DistributionResponseSerializer},
    )
    def get(self, request, format=None):
        query = DistributionQuerySerializer(data=request.query_params)
        query.is_valid(raise_exception=True)
        result = get_distribution(**query.validated_data)
        return Response(DistributionResponseSerializer(result).data)
