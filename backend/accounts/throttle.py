"""Failed-login throttling backed by Django's cache."""

from django.conf import settings
from django.core.cache import cache

from common.errors import RateLimitedError


def login_throttle_key(request, email):
    """Build the per-IP, per-email key used by the failed-login counter."""
    client_ip = request.META.get("REMOTE_ADDR", "unknown")
    return f"login-failures:{client_ip}:{email.strip().lower()}"


def check_login_throttle(key):
    """Raise a 429 error once the configured failure limit is reached."""
    failures = cache.get(key, 0)
    if failures >= settings.LOGIN_MAX_FAILURES:
        retry_after = settings.LOGIN_WINDOW_MINUTES * 60
        raise RateLimitedError(headers={"Retry-After": str(retry_after)})


def record_login_failure(key):
    """Increment the failure counter and start or refresh its window."""
    failures = cache.get(key, 0) + 1
    cache.set(
        key,
        failures,
        timeout=settings.LOGIN_WINDOW_MINUTES * 60,
    )


def clear_login_failures(key):
    """Remove the counter after a successful login."""
    cache.delete(key)
