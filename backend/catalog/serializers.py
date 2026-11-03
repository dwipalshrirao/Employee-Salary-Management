"""Response serializers for the public lookup payload."""

from rest_framework import serializers


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
