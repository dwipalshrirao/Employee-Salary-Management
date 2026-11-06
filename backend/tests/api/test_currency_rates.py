import pytest

from catalog.models import CurrencyRate
from employees.models import Employee
from tests.factories import make_country, make_currency_rate, make_employee

pytestmark = pytest.mark.django_db


@pytest.fixture
def reference_data():
    make_currency_rate("USD", 1.0)
    make_currency_rate("INR", 83.0)
    make_currency_rate("EUR", 0.92)
    make_country("US", "United States", "USD")
    make_country("IN", "India", "INR")
    make_country("DE", "Germany", "EUR")


def test_list_currency_rates_returns_sorted_items(auth_client, reference_data):
    response = auth_client.get("/api/currency-rates")

    assert response.status_code == 200
    assert response.json() == [
        {
            "currency_code": "EUR",
            "rate_per_usd": 0.92,
            "updated_at": "2026-01-01T12:00:00Z",
            "country_codes": ["DE"],
        },
        {
            "currency_code": "INR",
            "rate_per_usd": 83.0,
            "updated_at": "2026-01-01T12:00:00Z",
            "country_codes": ["IN"],
        },
        {
            "currency_code": "USD",
            "rate_per_usd": 1.0,
            "updated_at": "2026-01-01T12:00:00Z",
            "country_codes": ["US"],
        },
    ]


def test_get_currency_rate_returns_item(auth_client, reference_data):
    response = auth_client.get("/api/currency-rates/EUR")

    assert response.status_code == 200
    assert response.json()["currency_code"] == "EUR"
    assert response.json()["country_codes"] == ["DE"]


def test_get_currency_rate_returns_404_for_unknown_code(auth_client, reference_data):
    response = auth_client.get("/api/currency-rates/CAD")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_create_currency_rate_returns_created_item(auth_client, fixed_clock):
    response = auth_client.post(
        "/api/currency-rates",
        {"currency_code": "CAD", "rate_per_usd": 1.36},
        format="json",
    )

    assert response.status_code == 201
    assert response.json() == {
        "currency_code": "CAD",
        "rate_per_usd": 1.36,
        "updated_at": "2026-10-31T12:00:00Z",
        "country_codes": [],
    }
    assert CurrencyRate.objects.filter(pk="CAD").exists()


def test_create_currency_rate_rejects_duplicate(auth_client, reference_data):
    response = auth_client.post(
        "/api/currency-rates",
        {"currency_code": "EUR", "rate_per_usd": 0.93},
        format="json",
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


@pytest.mark.parametrize("code", ["eur", "EU", "EURO", "12A", ""])
def test_create_currency_rate_rejects_invalid_codes(auth_client, code):
    response = auth_client.post(
        "/api/currency-rates",
        {"currency_code": code, "rate_per_usd": 1.0},
        format="json",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize("rate", [0, -1, 1_000_001, "NaN", "Infinity", "nope"])
def test_create_currency_rate_rejects_invalid_rates(auth_client, rate):
    response = auth_client.post(
        "/api/currency-rates",
        {"currency_code": "CAD", "rate_per_usd": rate},
        format="json",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_create_currency_rate_rejects_unknown_fields(auth_client):
    response = auth_client.post(
        "/api/currency-rates",
        {"currency_code": "CAD", "rate_per_usd": 1.36, "name": "Canadian dollar"},
        format="json",
    )

    assert response.status_code == 422
    assert "name" in response.json()["error"]["details"]


def test_update_currency_rate_changes_rate(auth_client, reference_data, fixed_clock):
    response = auth_client.patch(
        "/api/currency-rates/EUR",
        {"rate_per_usd": 0.93},
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["rate_per_usd"] == 0.93
    assert response.json()["updated_at"] == "2026-10-31T12:00:00Z"
    assert CurrencyRate.objects.get(pk="EUR").rate_per_usd == 0.93


def test_update_currency_rate_rejects_usd(auth_client, reference_data):
    response = auth_client.patch(
        "/api/currency-rates/USD",
        {"rate_per_usd": 1.01},
        format="json",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_update_currency_rate_rejects_code_change(auth_client, reference_data):
    response = auth_client.patch(
        "/api/currency-rates/EUR",
        {"currency_code": "CAD", "rate_per_usd": 1.36},
        format="json",
    )

    assert response.status_code == 422
    assert "currency_code" in response.json()["error"]["details"]


def test_update_currency_rate_returns_404_for_unknown_code(auth_client):
    response = auth_client.patch(
        "/api/currency-rates/CAD",
        {"rate_per_usd": 1.36},
        format="json",
    )

    assert response.status_code == 404


def test_rate_change_updates_lookups_and_local_amount(
    auth_client,
    reference_data,
    fixed_clock,
):
    employee = make_employee(
        country=make_country("DE", "Germany", "EUR"),
        base_salary_cents=100_000,
        bonus_cents=0,
        allowances_cents=0,
    )
    before = auth_client.get(f"/api/employees/{employee.id}").json()

    response = auth_client.patch(
        "/api/currency-rates/EUR",
        {"rate_per_usd": 0.93},
        format="json",
    )
    lookups = auth_client.get("/api/lookups").json()
    after = auth_client.get(f"/api/employees/{employee.id}").json()

    assert response.status_code == 200
    assert before["local"]["base_salary_cents"] == 92_000
    assert after["local"]["base_salary_cents"] == 93_000
    assert after["base_salary_cents"] == 100_000
    assert Employee.objects.get(pk=employee.id).base_salary_cents == 100_000
    rate = next(item for item in lookups["currency_rates"] if item["currency_code"] == "EUR")
    assert rate["rate_per_usd"] == 0.93


def test_delete_currency_rate_removes_unused_currency(auth_client, reference_data):
    make_currency_rate("CAD", 1.36)

    response = auth_client.delete("/api/currency-rates/CAD")

    assert response.status_code == 204
    assert not CurrencyRate.objects.filter(pk="CAD").exists()


def test_delete_currency_rate_rejects_currency_used_by_a_country(
    auth_client,
    reference_data,
):
    response = auth_client.delete("/api/currency-rates/EUR")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert response.json()["error"]["details"]["country_codes"] == ["DE"]
    assert CurrencyRate.objects.filter(pk="EUR").exists()


def test_delete_currency_rate_rejects_usd(auth_client, reference_data):
    response = auth_client.delete("/api/currency-rates/USD")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


def test_delete_currency_rate_returns_404_for_unknown_code(auth_client):
    response = auth_client.delete("/api/currency-rates/CAD")

    assert response.status_code == 404
