import pytest
from rest_framework.exceptions import ValidationError

from catalog.models import CurrencyRate
from catalog.services import (
    create_currency_rate,
    delete_currency_rate,
    get_currency_rate,
    list_currency_rates,
    update_currency_rate,
)
from common.errors import ConflictError
from tests.factories import make_country, make_currency_rate

pytestmark = pytest.mark.django_db


@pytest.fixture
def rates():
    make_currency_rate("USD", 1.0)
    make_currency_rate("INR", 83.0)
    make_currency_rate("EUR", 0.92)
    make_country("US", "United States", "USD")
    make_country("IN", "India", "INR")
    make_country("DE", "Germany", "EUR")


def test_list_currency_rates_is_sorted_and_includes_country_codes(rates):
    result = list_currency_rates()

    assert [rate.currency_code for rate in result] == ["EUR", "INR", "USD"]
    assert result[0].country_codes == ["DE"]
    assert result[1].country_codes == ["IN"]
    assert result[2].country_codes == ["US"]


def test_get_currency_rate_includes_country_codes(rates):
    rate = get_currency_rate("INR")

    assert rate.currency_code == "INR"
    assert rate.rate_per_usd == 83.0
    assert rate.country_codes == ["IN"]


def test_create_currency_rate_uses_clock_and_starts_unused(fixed_clock):
    created = create_currency_rate(
        {"currency_code": "CAD", "rate_per_usd": 1.36},
        clock=fixed_clock,
    )

    assert created.currency_code == "CAD"
    assert created.rate_per_usd == 1.36
    assert created.updated_at == fixed_clock.now()
    assert created.country_codes == []


def test_create_currency_rate_rejects_duplicate_code(rates):
    with pytest.raises(ConflictError):
        create_currency_rate({"currency_code": "EUR", "rate_per_usd": 0.93})


@pytest.mark.parametrize("rate", [0, -1, 1_000_001, float("nan"), float("inf")])
def test_create_currency_rate_rejects_invalid_rates(rate):
    with pytest.raises(ValidationError):
        create_currency_rate({"currency_code": "CAD", "rate_per_usd": rate})


def test_update_currency_rate_changes_rate_and_timestamp(rates, fixed_clock):
    updated = update_currency_rate(
        "EUR",
        {"rate_per_usd": 0.93},
        clock=fixed_clock,
    )

    assert updated.rate_per_usd == 0.93
    assert updated.updated_at == fixed_clock.now()
    assert updated.country_codes == ["DE"]


def test_update_currency_rate_rejects_usd(rates):
    with pytest.raises(ValidationError):
        update_currency_rate("USD", {"rate_per_usd": 1.01})


def test_delete_currency_rate_rejects_currency_used_by_a_country(rates):
    with pytest.raises(ConflictError) as exc_info:
        delete_currency_rate("EUR")

    assert exc_info.value.details == {"country_codes": ["DE"]}
    assert CurrencyRate.objects.filter(pk="EUR").exists()


def test_delete_currency_rate_rejects_usd(rates):
    with pytest.raises(ConflictError):
        delete_currency_rate("USD")


def test_delete_currency_rate_removes_unused_currency(rates):
    make_currency_rate("CAD", 1.36)

    delete_currency_rate("CAD")

    assert not CurrencyRate.objects.filter(pk="CAD").exists()
