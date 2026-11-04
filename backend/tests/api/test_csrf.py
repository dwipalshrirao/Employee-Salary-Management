import pytest
from rest_framework.test import APIClient

WRITE_ROUTES = [
    ("post", "/api/auth/logout"),
    ("post", "/api/employees"),
    ("patch", "/api/employees/1"),
    ("post", "/api/employees/1/deactivate"),
    ("post", "/api/employees/1/reactivate"),
    ("post", "/api/bulk-updates/preview"),
    ("post", "/api/bulk-updates/apply"),
]

pytestmark = pytest.mark.django_db


def _client_with_session(email="hr@acme.example"):
    client = APIClient(enforce_csrf_checks=True)
    response = client.post(
        "/api/auth/login",
        {"email": email, "password": "correct-password"},
        format="json",
    )
    assert response.status_code == 200
    return client, response.json()["csrf_token"]


@pytest.mark.parametrize(("method", "path"), WRITE_ROUTES)
def test_write_routes_reject_missing_csrf(hr_user, method, path):
    client, _token = _client_with_session()

    response = getattr(client, method)(path, {}, format="json")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


@pytest.mark.parametrize(("method", "path"), WRITE_ROUTES)
def test_write_routes_accept_valid_csrf(hr_user, method, path):
    client, token = _client_with_session()
    request = getattr(client, method)

    response = request(
        path,
        {},
        format="json",
        HTTP_X_CSRF_TOKEN=token,
    )

    assert response.status_code != 403
