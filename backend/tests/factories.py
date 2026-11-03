"""Small factories for readable employee API tests."""

from datetime import UTC, date, datetime
from itertools import count

from catalog.models import Country, CurrencyRate, Department, JobTitle
from employees.models import Employee

DEFAULT_NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
_employee_ids = count(1)


def make_currency_rate(code="USD", rate_per_usd=1.0):
    return CurrencyRate.objects.get_or_create(
        currency_code=code,
        defaults={"rate_per_usd": rate_per_usd, "updated_at": DEFAULT_NOW},
    )[0]


def make_country(code="US", name="United States", currency_code="USD"):
    make_currency_rate(currency_code)
    return Country.objects.get_or_create(
        code=code,
        defaults={"name": name, "currency_code_id": currency_code},
    )[0]


def make_department(name="Engineering"):
    return Department.objects.get_or_create(name=name)[0]


def make_job_title(name="Software Engineer", level=2):
    return JobTitle.objects.get_or_create(name=name, defaults={"level": level})[0]


def make_employee(**overrides):
    index = next(_employee_ids)
    data = {
        "full_name": f"Employee {index}",
        "email": f"employee{index}@acme.example",
        "department": make_department(),
        "job_title": make_job_title(),
        "country": make_country(),
        "manager": None,
        "hire_date": date(2021, 1, 1),
        "status": Employee.Status.ACTIVE,
        "base_salary_cents": 5_000_000,
        "bonus_cents": 500_000,
        "allowances_cents": 200_000,
        "created_at": DEFAULT_NOW,
        "updated_at": DEFAULT_NOW,
    }
    data.update(overrides)
    return Employee.objects.create(**data)
