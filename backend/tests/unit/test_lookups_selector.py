from datetime import UTC, datetime

import pytest

from catalog.models import Country, CurrencyRate, Department, JobTitle
from catalog.selectors import get_lookups


@pytest.mark.django_db
def test_get_lookups_returns_reference_data_in_stable_order():
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
    Department.objects.create(name="Sales")
    Department.objects.create(name="Engineering")
    JobTitle.objects.create(name="Software Engineer", level=2)
    JobTitle.objects.create(name="Account Executive", level=2)

    lookups = get_lookups()

    assert [country.code for country in lookups["countries"]] == ["IN", "US"]
    assert [department.name for department in lookups["departments"]] == [
        "Engineering",
        "Sales",
    ]
    assert [title.name for title in lookups["job_titles"]] == [
        "Account Executive",
        "Software Engineer",
    ]
    assert [rate.currency_code for rate in lookups["currency_rates"]] == [
        "INR",
        "USD",
    ]
