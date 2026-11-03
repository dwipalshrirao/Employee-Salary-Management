import pytest


def test_schema_endpoint_is_not_exposed(client):
    response = client.get("/api/schema/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_swagger_ui_is_served(client):
    response = client.get("/api/docs/")

    assert response.status_code == 200
    assert b"swagger-ui" in response.content
    assert b"/api/docs/schema/" in response.content
    assert b"data:application/vnd.oai.openapi" not in response.content
    assert b"/api/schema/" not in response.content


@pytest.mark.django_db
def test_swagger_schema_endpoint_serves_resolvable_document(client):
    response = client.get(
        "/api/docs/schema/", HTTP_ACCEPT="application/vnd.oai.openapi+json"
    )

    assert response.status_code == 200
    schema = response.json()
    assert "/api/health" in schema["paths"]
    assert "HealthResponse" in schema["components"]["schemas"]
