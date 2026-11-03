"""Login, logout and current-user API views."""

from django.contrib.auth import logout
from django.middleware.csrf import get_token
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.status import HTTP_204_NO_CONTENT
from rest_framework.views import APIView

from accounts.serializers import (
    AuthResponseSerializer,
    LoginRequestSerializer,
)
from accounts.services import login_user


def _auth_payload(request, user):
    return AuthResponseSerializer(
        {"user": user, "csrf_token": get_token(request)}
    ).data


class LoginView(APIView):
    """Authenticate an HR user and establish a session."""

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="auth-login",
        tags=["auth"],
        request=LoginRequestSerializer,
        responses={200: AuthResponseSerializer},
    )
    def post(self, request, format=None):
        serializer = LoginRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = login_user(
            request,
            serializer.validated_data["email"],
            serializer.validated_data["password"],
        )
        return Response(_auth_payload(request, user))


class LogoutView(APIView):
    """End the current session and clear its cookie."""

    @extend_schema(
        operation_id="auth-logout",
        tags=["auth"],
        request=None,
        responses={204: None},
    )
    def post(self, request, format=None):
        logout(request)
        return Response(status=HTTP_204_NO_CONTENT)


class MeView(APIView):
    """Return the signed-in user and the current CSRF token."""

    @extend_schema(
        operation_id="auth-me",
        tags=["auth"],
        responses={200: AuthResponseSerializer},
    )
    def get(self, request, format=None):
        return Response(_auth_payload(request, request.user))
