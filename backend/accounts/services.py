"""Authentication rules and session writes."""

from django.contrib.auth import authenticate, login
from rest_framework.exceptions import AuthenticationFailed

from accounts.throttle import (
    check_login_throttle,
    clear_login_failures,
    login_throttle_key,
    record_login_failure,
)
from common.clock import get_clock

INVALID_CREDENTIALS = "Invalid email or password"


def login_user(request, email, password):
    """Authenticate, apply the throttle, and create a new session."""
    throttle_key = login_throttle_key(request, email)
    check_login_throttle(throttle_key)

    user = authenticate(
        request=request,
        username=email,
        password=password,
    )
    if user is None:
        record_login_failure(throttle_key)
        raise AuthenticationFailed(INVALID_CREDENTIALS)

    clear_login_failures(throttle_key)
    login(request, user)

    now = get_clock().now()
    request.session["login_at"] = now.isoformat()
    request.session["last_seen_at"] = now.isoformat()
    return user
