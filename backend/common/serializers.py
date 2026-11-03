from django.conf import settings
from rest_framework import serializers


class PageQuerySerializer(serializers.Serializer):
    """Shared 1-based pagination query parameters."""

    page = serializers.IntegerField(min_value=1, default=1)
    page_size = serializers.IntegerField(
        min_value=1,
        max_value=settings.MAX_PAGE_SIZE,
        default=25,
    )


class StrictSerializer(serializers.Serializer):
    """Reject unknown input fields instead of silently ignoring them."""

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unknown_fields = set(data.keys()) - set(self.fields)
            if unknown_fields:
                raise serializers.ValidationError(
                    {
                        field: ["Unknown field."]
                        for field in sorted(unknown_fields)
                    }
                )
        return super().to_internal_value(data)


class HealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
