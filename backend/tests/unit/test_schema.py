from datetime import UTC, date, datetime

import pytest
from django.core.management import call_command
from django.db import IntegrityError, connection, transaction
from django.db.models import ProtectedError

from catalog.models import Country, CurrencyRate, Department, JobTitle
from employees.models import Employee, SalaryHistory

pytestmark = pytest.mark.django_db

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def make_reference_data():
    currency = CurrencyRate.objects.create(
        currency_code="USD",
        rate_per_usd=1.0,
        updated_at=NOW,
    )
    country = Country.objects.create(
        code="US",
        name="United States",
        currency_code=currency,
    )
    department = Department.objects.create(name="Engineering")
    job_title = JobTitle.objects.create(name="Software Engineer", level=2)
    return country, department, job_title


def make_employee(**overrides):
    country, department, job_title = make_reference_data()
    data = {
        "full_name": "Asha Patel",
        "email": "asha.patel@example.com",
        "country": country,
        "department": department,
        "job_title": job_title,
        "hire_date": date(2021, 4, 12),
        "base_salary_cents": 4_500_000,
        "bonus_cents": 450_000,
        "allowances_cents": 180_000,
        "created_at": NOW,
        "updated_at": NOW,
    }
    data.update(overrides)
    return Employee.objects.create(**data)


def assert_integrity_error(operation):
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            operation()


def test_base_salary_must_be_positive():
    assert_integrity_error(lambda: make_employee(base_salary_cents=0))


@pytest.mark.parametrize("field", ["bonus_cents", "allowances_cents"])
def test_additional_pay_must_be_non_negative(field):
    assert_integrity_error(lambda: make_employee(**{field: -1}))


def test_status_must_be_valid():
    assert_integrity_error(lambda: make_employee(status="retired"))


def test_employee_cannot_manage_themselves():
    employee = make_employee()

    assert_integrity_error(
        lambda: Employee.objects.filter(pk=employee.pk).update(manager_id=employee.pk)
    )


def test_employee_email_is_unique_case_insensitively():
    make_employee(email="asha.patel@example.com")

    assert_integrity_error(lambda: make_employee(email="ASHA.PATEL@example.com"))


def test_total_compensation_is_generated_from_components():
    employee = make_employee(
        base_salary_cents=4_500_000,
        bonus_cents=450_000,
        allowances_cents=180_000,
    )

    employee.refresh_from_db()

    assert employee.total_comp_cents == 5_130_000


def test_salary_history_is_append_only():
    country, department, job_title = make_reference_data()
    employee = Employee.objects.create(
        full_name="Asha Patel",
        email="asha.patel@example.com",
        country=country,
        department=department,
        job_title=job_title,
        hire_date=date(2021, 4, 12),
        base_salary_cents=4_500_000,
        created_at=NOW,
        updated_at=NOW,
    )
    history = SalaryHistory.objects.create(
        employee=employee,
        effective_date=date(2021, 4, 12),
        change_type="hire",
        reason="New hire",
        base_salary_cents=4_500_000,
        bonus_cents=0,
        allowances_cents=0,
        created_at=NOW,
    )

    with pytest.raises(ValueError, match="append-only"):
        history.save()


def test_salary_history_change_type_must_be_valid():
    country, department, job_title = make_reference_data()
    employee = Employee.objects.create(
        full_name="Asha Patel",
        email="asha.patel@example.com",
        country=country,
        department=department,
        job_title=job_title,
        hire_date=date(2021, 4, 12),
        base_salary_cents=4_500_000,
        created_at=NOW,
        updated_at=NOW,
    )

    assert_integrity_error(
        lambda: SalaryHistory.objects.create(
            employee=employee,
            effective_date=date(2021, 4, 12),
            change_type="promotion",
            base_salary_cents=4_500_000,
            bonus_cents=0,
            allowances_cents=0,
            created_at=NOW,
        )
    )


def test_referenced_reference_data_is_protected():
    employee = make_employee()

    with pytest.raises(ProtectedError):
        with transaction.atomic():
            employee.department.delete()


def test_schema_indexes_exist():
    with connection.cursor() as cursor:
        constraints = connection.introspection.get_constraints(cursor, "employees")

    for name in {
        "idx_emp_status_country",
        "idx_emp_status_dept",
        "idx_emp_title",
        "idx_emp_manager",
        "idx_emp_name",
    }:
        assert name in constraints


def test_migrations_are_up_to_date():
    call_command("makemigrations", "--check", "--dry-run", verbosity=0)
