from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.status import HTTP_201_CREATED, HTTP_204_NO_CONTENT
from rest_framework.views import APIView

from catalog.selectors import get_lookups
from catalog.serializers import (
    CurrencyRateCreateSerializer,
    CurrencyRateItemSerializer,
    CurrencyRateUpdateSerializer,
    LookupsResponseSerializer,
)
from catalog.services import (
    create_currency_rate,
    delete_currency_rate,
    get_currency_rate,
    list_currency_rates,
    update_currency_rate,
)


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


class CurrencyRateListView(APIView):
    """List and create currency rates."""

    @extend_schema(
        operation_id="currency-rates-list",
        tags=["catalog"],
        responses={200: CurrencyRateItemSerializer(many=True)},
    )
    def get(self, request, format=None):
        rates = list_currency_rates()
        return Response(CurrencyRateItemSerializer(rates, many=True).data)

    @extend_schema(
        operation_id="currency-rates-create",
        tags=["catalog"],
        request=CurrencyRateCreateSerializer,
        responses={201: CurrencyRateItemSerializer},
    )
    def post(self, request, format=None):
        serializer = CurrencyRateCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rate = create_currency_rate(serializer.validated_data)
        return Response(
            CurrencyRateItemSerializer(rate).data,
            status=HTTP_201_CREATED,
        )


class CurrencyRateDetailView(APIView):
    """Read, update or delete one currency rate."""

    @extend_schema(
        operation_id="currency-rates-detail",
        tags=["catalog"],
        responses={200: CurrencyRateItemSerializer},
    )
    def get(self, request, code, format=None):
        rate = get_currency_rate(code)
        return Response(CurrencyRateItemSerializer(rate).data)

    @extend_schema(
        operation_id="currency-rates-update",
        tags=["catalog"],
        request=CurrencyRateUpdateSerializer,
        responses={200: CurrencyRateItemSerializer},
    )
    def patch(self, request, code, format=None):
        serializer = CurrencyRateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rate = update_currency_rate(code, serializer.validated_data)
        return Response(CurrencyRateItemSerializer(rate).data)

    @extend_schema(
        operation_id="currency-rates-delete",
        tags=["catalog"],
        responses={204: None},
    )
    def delete(self, request, code, format=None):
        delete_currency_rate(code)
        return Response(status=HTTP_204_NO_CONTENT)
