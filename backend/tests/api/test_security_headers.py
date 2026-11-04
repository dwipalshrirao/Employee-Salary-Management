import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def assert_security_headers(response):
    assert response["X-Content-Type-Options"] == "nosniff"
    assert response["X-Frame-Options"] == "DENY"
    assert response["Referrer-Policy"] == "no-referrer"
    assert response["Cache-Control"] in {"no-store", "private, max-age=60"}


def test_health_response_has_security_headers(client):
    response = client.get("/api/health")

    assert_security_headers(response)


@pytest.mark.parametrize(
    "path",
    ["/api/health", "/api/auth/me", "/api/employees", "/api/lookups"],
)
def test_successful_responses_have_security_headers(auth_client, path):
    response = auth_client.get(path)

    assert response.status_code == 200
    assert_security_headers(response)


def test_error_responses_have_security_headers(auth_client):
    anonymous = APIClient()
    responses = [
        anonymous.get("/api/lookups"),
        anonymous.get("/api/does-not-exist"),
        auth_client.get("/api/employees", {"page_size": 101}),
    ]

    assert [response.status_code for response in responses] == [401, 404, 422]
    for response in responses:
        assert_security_headers(response)


def test_lookups_keeps_its_private_cache_header(auth_client):
    response = auth_client.get("/api/lookups")

    assert response["Cache-Control"] == "private, max-age=60"
