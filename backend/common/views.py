from drf_spectacular.utils import OpenApiExample, extend_schema
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.serializers import HealthResponseSerializer


class HealthView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="health",
        tags=["health"],
        responses={200: HealthResponseSerializer},
        examples=[OpenApiExample("ok", value={"status": "ok"}, response_only=True)],
    )
    def get(self, request, format=None):
        return Response({"status": "ok"})


class ApiDocsView(SpectacularSwaggerView):
    """Serve Swagger UI for local API exploration."""

    url_name = "docs-schema"
