from datetime import date
from uuid import uuid4

import pytest

from employees.models import SalaryHistory
from tests.factories import (
    make_country,
    make_currency_rate,
    make_employee,
    make_salary_history,
)

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "path",
    [
        "/api/employees/1",
        "/api/employees/1/history",
        "/api/employees/1/direct-reports",
    ],
)
def test_employee_detail_routes_require_authentication(client, path):
    response = client.get(path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_employee_detail_includes_local_currency_and_direct_report_count(auth_client):
    make_currency_rate("INR", 83.0)
    india = make_country("IN", "India", "INR")
    manager = make_employee(full_name="Ravi Shah", email="ravi@acme.example")
    employee = make_employee(
        full_name="Asha Patel",
        email="asha@acme.example",
        country=india,
        manager=manager,
        base_salary_cents=4_500_000,
        bonus_cents=450_000,
        allowances_cents=180_000,
    )
    make_employee(
        full_name="Active Report",
        email="active@acme.example",
        manager=employee,
    )
    make_employee(
        full_name="Inactive Report",
        email="inactive@acme.example",
        manager=employee,
        status="inactive",
    )

    response = auth_client.get(f"/api/employees/{employee.id}")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == employee.id
    assert payload["full_name"] == "Asha Patel"
    assert payload["manager"] == {"id": manager.id, "full_name": "Ravi Shah"}
    assert payload["direct_reports_count"] == 2
    assert payload["local"] == {
        "currency_code": "INR",
        "rate_per_usd": 83.0,
        "base_salary_cents": 373_500_000,
        "bonus_cents": 37_350_000,
        "allowances_cents": 14_940_000,
        "total_comp_cents": 425_790_000,
    }
    assert payload["created_at"] == "2026-01-01T12:00:00Z"
    assert payload["updated_at"] == "2026-01-01T12:00:00Z"


def test_employee_detail_returns_404_for_unknown_employee(auth_client):
    response = auth_client.get("/api/employees/999999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_direct_reports_are_paginated(auth_client):
    manager = make_employee(full_name="Manager", email="manager@acme.example")
    reports = [
        make_employee(
            full_name=f"Report {index}",
            email=f"report{index}@acme.example",
            manager=manager,
            status="inactive" if index == 2 else "active",
        )
        for index in range(3)
    ]

    response = auth_client.get(
        f"/api/employees/{manager.id}/direct-reports",
        {"page": 2, "page_size": 2},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["page"] == 2
    assert payload["page_size"] == 2
    assert [item["id"] for item in payload["items"]] == [reports[2].id]
    assert payload["items"][0]["status"] == "inactive"


def test_direct_reports_return_404_for_unknown_manager(auth_client):
    response = auth_client.get("/api/employees/999999/direct-reports")

    assert response.status_code == 404


def test_employee_history_is_newest_first_and_builds_previous_values(auth_client):
    employee = make_employee()
    hire = make_salary_history(
        employee=employee,
        effective_date=date(2021, 1, 1),
        change_type=SalaryHistory.ChangeType.HIRE,
        reason="New hire",
        base_salary_cents=4_000_000,
        bonus_cents=400_000,
        allowances_cents=100_000,
    )
    raise_row = make_salary_history(
        employee=employee,
        effective_date=date(2022, 1, 1),
        change_type=SalaryHistory.ChangeType.MANUAL_EDIT,
        reason="Annual review",
        batch_id=uuid4(),
        base_salary_cents=4_500_000,
        bonus_cents=450_000,
        allowances_cents=150_000,
        prev_base_salary_cents=hire.base_salary_cents,
        prev_bonus_cents=hire.bonus_cents,
        prev_allowances_cents=hire.allowances_cents,
    )
    newest = make_salary_history(
        employee=employee,
        effective_date=date(2023, 1, 1),
        change_type=SalaryHistory.ChangeType.BULK_UPDATE,
        reason="FY24 raise",
        base_salary_cents=5_000_000,
        bonus_cents=500_000,
        allowances_cents=200_000,
        prev_base_salary_cents=raise_row.base_salary_cents,
        prev_bonus_cents=raise_row.bonus_cents,
        prev_allowances_cents=raise_row.allowances_cents,
    )

    response = auth_client.get(f"/api/employees/{employee.id}/history")

    assert response.status_code == 200
    payload = response.json()
    assert [item["id"] for item in payload] == [newest.id, raise_row.id, hire.id]
    assert payload[0]["new"] == {
        "base_salary_cents": 5_000_000,
        "bonus_cents": 500_000,
        "allowances_cents": 200_000,
        "total_comp_cents": 5_700_000,
    }
    assert payload[0]["previous"] == {
        "base_salary_cents": 4_500_000,
        "bonus_cents": 450_000,
        "allowances_cents": 150_000,
        "total_comp_cents": 5_100_000,
    }
    assert payload[2]["previous"] is None


def test_employee_history_returns_404_for_unknown_employee(auth_client):
    response = auth_client.get("/api/employees/999999/history")

    assert response.status_code == 404
