"""Query and response serializers for analytics endpoints."""

from rest_framework import serializers


class AnalyticsQuerySerializer(serializers.Serializer):
    country_code = serializers.CharField(
        max_length=2,
        required=False,
        allow_blank=True,
    )
    department_id = serializers.IntegerField(required=False)
    job_title_id = serializers.IntegerField(required=False)
    measure = serializers.ChoiceField(
        choices=("total", "base"),
        default="total",
    )
    include_inactive = serializers.BooleanField(default=False)


class SummaryQuerySerializer(AnalyticsQuerySerializer):
    pass


class BreakdownQuerySerializer(AnalyticsQuerySerializer):
    group_by = serializers.ChoiceField(
        choices=("country", "department", "job_title"),
    )
    sort_by = serializers.ChoiceField(
        choices=("name", "headcount", "total", "avg", "min", "max"),
        default="avg",
    )
    sort_dir = serializers.ChoiceField(choices=("asc", "desc"), default="desc")
    limit = serializers.IntegerField(min_value=1, max_value=100, required=False)


class SummaryComponentsSerializer(serializers.Serializer):
    base_cents = serializers.IntegerField()
    bonus_cents = serializers.IntegerField()
    allowances_cents = serializers.IntegerField()


class SummaryResponseSerializer(serializers.Serializer):
    headcount = serializers.IntegerField()
    total_cents = serializers.IntegerField()
    avg_cents = serializers.IntegerField()
    min_cents = serializers.IntegerField()
    max_cents = serializers.IntegerField()
    components = SummaryComponentsSerializer()
    country_count = serializers.IntegerField()
    department_count = serializers.IntegerField()


class BreakdownRowSerializer(serializers.Serializer):
    key = serializers.CharField()
    name = serializers.CharField()
    headcount = serializers.IntegerField()
    total_cents = serializers.IntegerField()
    avg_cents = serializers.IntegerField()
    min_cents = serializers.IntegerField()
    max_cents = serializers.IntegerField()


class BreakdownResponseSerializer(serializers.Serializer):
    group_by = serializers.CharField()
    measure = serializers.CharField()
    rows = BreakdownRowSerializer(many=True)
