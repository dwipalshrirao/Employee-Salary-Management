"""Session authentication with the project's absolute and idle limits."""

from datetime import UTC, datetime, timedelta

from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension
from rest_framework.authentication import SessionAuthentication

from common.clock import get_clock


def _parse_timestamp(value):
    """Parse an ISO timestamp stored in the session, or return ``None``."""
    if isinstance(value, datetime):
        timestamp = value
    else:
        try:
            timestamp = datetime.fromisoformat(value)
        except (TypeError, ValueError):
            return None

    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=UTC)
    return timestamp


class SessionAuth(SessionAuthentication):
    """Validate a session user against the absolute and idle limits."""

    def authenticate(self, request):
        user = getattr(request._request, "user", None)
        if user is None or not user.is_authenticated:
            return None

        now = get_clock().now()
        if self._session_is_expired(request, user, now):
            return None

        # Let DRF enforce CSRF only after the session is known to be valid.
        result = super().authenticate(request)
        if result is None:
            return None

        self._touch_last_seen(request, now)
        return result

    def authenticate_header(self, request):
        # Without this DRF returns 403 for anonymous requests.
        return "Session"

    def _session_is_expired(self, request, user, now):
        if not user.is_active:
            request.session.flush()
            return True

        session = request.session
        login_at = _parse_timestamp(session.get("login_at"))
        last_seen_at = _parse_timestamp(session.get("last_seen_at"))

        if login_at is None or last_seen_at is None:
            session.flush()
            return True

        if now - login_at > timedelta(hours=settings.SESSION_ABSOLUTE_HOURS):
            session.flush()
            return True

        if now - last_seen_at > timedelta(minutes=settings.SESSION_IDLE_MINUTES):
            session.flush()
            return True

        return False

    def _touch_last_seen(self, request, now):
        session = request.session
        last_seen_at = _parse_timestamp(session.get("last_seen_at"))
        if last_seen_at is None or now - last_seen_at >= timedelta(minutes=1):
            session["last_seen_at"] = now.isoformat()
            session.modified = True


class SessionAuthScheme(OpenApiAuthenticationExtension):
    """Document the session cookie used by the API."""

    target_class = "accounts.auth.SessionAuth"
    name = "sessionAuth"

    def get_security_definition(self, auto_schema):
        return {
            "type": "apiKey",
            "in": "cookie",
            "name": settings.SESSION_COOKIE_NAME,
        }
