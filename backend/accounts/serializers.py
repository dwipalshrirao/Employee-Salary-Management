"""Serializers for authentication requests and responses."""

from rest_framework import serializers

from common.serializers import StrictSerializer


class LoginRequestSerializer(StrictSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)


class AuthUserSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    full_name = serializers.CharField()


class AuthResponseSerializer(serializers.Serializer):
    user = AuthUserSerializer()
    csrf_token = serializers.CharField()
