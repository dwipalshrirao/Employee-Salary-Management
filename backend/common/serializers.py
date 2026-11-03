from rest_framework import serializers


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
