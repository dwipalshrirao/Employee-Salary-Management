from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from catalog.selectors import get_lookups
from catalog.serializers import LookupsResponseSerializer


class LookupsView(APIView):
    """Return the reference data used by employee forms and filters."""

    @extend_schema(
        operation_id="lookups",
        tags=["catalog"],
        responses={200: LookupsResponseSerializer},
    )
    def get(self, request, format=None):
        response = Response(LookupsResponseSerializer(get_lookups()).data)
        # The middleware preserves this header instead of forcing no-store.
        response["Cache-Control"] = "private, max-age=60"
        return response
