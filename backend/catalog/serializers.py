"""Serializers for lookup data and currency rate maintenance."""

from rest_framework import serializers

from common.serializers import StrictSerializer


class CountryLookupSerializer(serializers.Serializer):
    """Country row with the currency code flattened for easy client use."""

    code = serializers.CharField()
    name = serializers.CharField()
    currency_code = serializers.CharField(source="currency_code_id")


class DepartmentLookupSerializer(serializers.Serializer):
    """Department option used by employee filters and forms."""

    id = serializers.IntegerField()
    name = serializers.CharField()


class JobTitleLookupSerializer(serializers.Serializer):
    """Job title option including its compensation level."""

    id = serializers.IntegerField()
    name = serializers.CharField()
    level = serializers.IntegerField()


class CurrencyRateLookupSerializer(serializers.Serializer):
    """USD conversion rate used for approximate local-currency display."""

    currency_code = serializers.CharField()
    rate_per_usd = serializers.FloatField()
    updated_at = serializers.DateTimeField()


class LookupsResponseSerializer(serializers.Serializer):
    """Full lookup payload consumed once by the frontend query cache."""

    countries = CountryLookupSerializer(many=True)
    departments = DepartmentLookupSerializer(many=True)
    job_titles = JobTitleLookupSerializer(many=True)
    currency_rates = CurrencyRateLookupSerializer(many=True)


class CurrencyRateItemSerializer(serializers.Serializer):
    """Currency rate row with the countries that depend on it."""

    currency_code = serializers.CharField()
    rate_per_usd = serializers.FloatField()
    updated_at = serializers.DateTimeField()
    country_codes = serializers.ListField(child=serializers.CharField())


class CurrencyRateCreateSerializer(StrictSerializer):
    """Create a currency rate with an immutable three-letter code."""

    currency_code = serializers.RegexField(
        r"^[A-Z]{3}$",
        error_messages={
            "invalid": "Currency code must be three uppercase letters.",
        },
    )
    rate_per_usd = serializers.FloatField()


class CurrencyRateUpdateSerializer(StrictSerializer):
    """Update only the conversion rate; the code is URL-addressed."""

    rate_per_usd = serializers.FloatField()
