from datetime import UTC, datetime

import pytest
from drf_spectacular.generators import SchemaGenerator

from catalog.models import Country, CurrencyRate, Department, JobTitle


@pytest.fixture
def reference_data():
    CurrencyRate.objects.create(
        currency_code="USD",
        rate_per_usd=1.0,
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    CurrencyRate.objects.create(
        currency_code="INR",
        rate_per_usd=83.0,
        updated_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    Country.objects.create(code="US", name="United States", currency_code_id="USD")
    Country.objects.create(code="IN", name="India", currency_code_id="INR")
    Department.objects.create(name="Engineering")
    JobTitle.objects.create(name="Software Engineer", level=2)


@pytest.mark.django_db
def test_lookups_requires_authentication(client, reference_data):
    response = client.get("/api/lookups")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


@pytest.mark.django_db
def test_lookups_returns_reference_data(auth_client, reference_data):
    response = auth_client.get("/api/lookups")

    assert response.status_code == 200
    assert response.json() == {
        "countries": [
            {"code": "IN", "name": "India", "currency_code": "INR"},
            {"code": "US", "name": "United States", "currency_code": "USD"},
        ],
        "departments": [{"id": 1, "name": "Engineering"}],
        "job_titles": [{"id": 1, "name": "Software Engineer", "level": 2}],
        "currency_rates": [
            {
                "currency_code": "INR",
                "rate_per_usd": 83.0,
                "updated_at": "2026-01-01T00:00:00Z",
            },
            {
                "currency_code": "USD",
                "rate_per_usd": 1.0,
                "updated_at": "2026-01-01T00:00:00Z",
            },
        ],
    }
    assert response["Cache-Control"] == "private, max-age=60"


def test_lookups_schema_documents_session_cookie_auth():
    schema = SchemaGenerator().get_schema(request=None, public=True)

    assert schema["paths"]["/api/lookups"]["get"]["security"] == [{"sessionAuth": []}]
    scheme = schema["components"]["securitySchemes"]["sessionAuth"]
    assert scheme["type"] == "apiKey"
    assert scheme["in"] == "cookie"
    assert scheme["name"] == "acme_session"
