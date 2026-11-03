from datetime import UTC, datetime, timedelta

import pytest
from django.conf import settings
from django.core.cache import cache
from django.test import override_settings
from rest_framework.test import APIClient

from accounts.models import HrUser
from common.clock import Clock

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_login_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def hr_user():
    return HrUser.objects.create_user(
        email="hr@acme.example",
        full_name="HR Manager",
        password="correct-password",
    )


@pytest.fixture
def auth_clock(monkeypatch):
    current = [datetime(2026, 10, 31, 12, 0, tzinfo=UTC)]
    monkeypatch.setattr(Clock, "now", lambda self: current[0])
    monkeypatch.setattr(Clock, "today", lambda self: current[0].date())
    return current


def _login(client, email="hr@acme.example", password="correct-password"):
    return client.post(
        "/api/auth/login",
        {"email": email, "password": password},
        format="json",
    )


def test_wrong_password_and_unknown_email_return_the_same_error(client, hr_user):
    wrong_password = _login(client, password="wrong-password")
    unknown_email = _login(
        client,
        email="unknown@acme.example",
        password="wrong-password",
    )

    assert wrong_password.status_code == 401
    assert unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.json()["error"]["message"] == "Invalid email or password"


@override_settings(SESSION_COOKIE_SECURE=True)
def test_login_sets_cookie_flags_and_rotates_the_session_key(client, hr_user):
    session = client.session
    session["pre_login"] = "marker"
    session.save()
    old_key = client.cookies[settings.SESSION_COOKIE_NAME].value

    response = _login(client)

    assert response.status_code == 200
    cookie = response.cookies[settings.SESSION_COOKIE_NAME]
    assert cookie["httponly"] is True
    assert cookie["samesite"] == "Lax"
    assert cookie["secure"] is True
    assert cookie.value != old_key


def test_login_is_exempt_from_csrf(hr_user):
    client = APIClient(enforce_csrf_checks=True)

    response = _login(client)

    assert response.status_code == 200


def test_login_and_me_return_the_user_and_csrf_token(client, hr_user):
    login_response = _login(client)
    me_response = client.get("/api/auth/me")

    assert login_response.status_code == 200
    assert me_response.status_code == 200
    for response in (login_response, me_response):
        payload = response.json()
        assert payload["user"] == {
            "id": hr_user.id,
            "email": hr_user.email,
            "full_name": hr_user.full_name,
        }
        assert payload["csrf_token"]


def test_missing_csrf_on_logout_returns_csrf_failed(hr_user):
    client = APIClient(enforce_csrf_checks=True)
    assert _login(client).status_code == 200

    response = client.post("/api/auth/logout", format="json")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


def test_unauthenticated_request_returns_401_not_403(client):
    response = client.get("/api/lookups")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@override_settings(LOGIN_MAX_FAILURES=2, LOGIN_WINDOW_MINUTES=15)
def test_login_throttle_returns_429_with_retry_after(client, hr_user):
    for _ in range(2):
        assert _login(client, password="wrong-password").status_code == 401

    response = _login(client, password="wrong-password")

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    assert response["Retry-After"].isdigit()


def test_session_expires_after_the_absolute_limit(client, hr_user, auth_clock):
    assert _login(client).status_code == 200
    now = auth_clock[0]
    session = client.session
    session["login_at"] = (
        now - timedelta(hours=settings.SESSION_ABSOLUTE_HOURS + 1)
    ).isoformat()
    session["last_seen_at"] = now.isoformat()
    session.save()

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_session_expires_after_the_idle_limit(client, hr_user, auth_clock):
    assert _login(client).status_code == 200
    now = auth_clock[0]
    session = client.session
    session["login_at"] = now.isoformat()
    session["last_seen_at"] = (
        now - timedelta(minutes=settings.SESSION_IDLE_MINUTES + 1)
    ).isoformat()
    session.save()

    response = client.get("/api/auth/me")

    assert response.status_code == 401


def test_logout_ends_the_session(client, hr_user):
    login_response = _login(client)
    assert login_response.status_code == 200

    logout_response = client.post(
        "/api/auth/logout",
        HTTP_X_CSRF_TOKEN=login_response.json()["csrf_token"],
        format="json",
    )
    me_response = client.get("/api/auth/me")

    assert logout_response.status_code == 204
    assert me_response.status_code == 401
