from datetime import date
from uuid import uuid4

import pytest

from employees.models import Employee, SalaryHistory
from tests.factories import make_employee, make_salary_history

pytestmark = pytest.mark.django_db


def test_salary_history_requires_authentication(client):
    response = client.get("/api/salary-history")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_salary_history_returns_items_with_employee_and_salary_blocks(auth_client):
    employee = make_employee(
        full_name="Asha Patel",
        email="asha@acme.example",
        status=Employee.Status.INACTIVE,
    )
    batch_id = uuid4()
    hire = make_salary_history(
        employee=employee,
        effective_date=date(2021, 6, 1),
        change_type=SalaryHistory.ChangeType.HIRE,
        reason="New hire",
        base_salary_cents=4_000_000,
        bonus_cents=400_000,
        allowances_cents=100_000,
    )
    newest = make_salary_history(
        employee=employee,
        effective_date=date(2026, 1, 1),
        change_type=SalaryHistory.ChangeType.BULK_UPDATE,
        reason="FY27 raise",
        batch_id=batch_id,
        base_salary_cents=5_000_000,
        bonus_cents=500_000,
        allowances_cents=200_000,
        prev_base_salary_cents=hire.base_salary_cents,
        prev_bonus_cents=hire.bonus_cents,
        prev_allowances_cents=hire.allowances_cents,
    )

    response = auth_client.get("/api/salary-history")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["page"] == 1
    assert payload["page_size"] == 25
    assert [item["id"] for item in payload["items"]] == [newest.id, hire.id]
    assert payload["items"][0] == {
        "id": newest.id,
        "employee": {
            "id": employee.id,
            "full_name": "Asha Patel",
            "email": "asha@acme.example",
        },
        "effective_date": "2026-01-01",
        "change_type": "bulk_update",
        "reason": "FY27 raise",
        "batch_id": str(batch_id),
        "created_at": "2026-01-01T12:00:00Z",
        "new": {
            "base_salary_cents": 5_000_000,
            "bonus_cents": 500_000,
            "allowances_cents": 200_000,
            "total_comp_cents": 5_700_000,
        },
        "previous": {
            "base_salary_cents": 4_000_000,
            "bonus_cents": 400_000,
            "allowances_cents": 100_000,
            "total_comp_cents": 4_500_000,
        },
    }
    assert payload["items"][1]["previous"] is None


@pytest.mark.parametrize(
    "params",
    [
        {"sort_by": "id;drop table salary_history"},
        {"sort_dir": "sideways"},
        {"page": "0"},
        {"page_size": "101"},
        {"employee": "x" * 101},
        {"reason": "x" * 101},
        {"change_type": "raise"},
        {"date_from": "not-a-date"},
        {"date_from": "2026-02-01", "date_to": "2026-01-01"},
        {"batch_id": "not-a-uuid"},
    ],
)
def test_invalid_history_query_parameters_return_422(auth_client, params):
    response = auth_client.get("/api/salary-history", params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_salary_history_returns_empty_page(auth_client):
    response = auth_client.get("/api/salary-history")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 25,
    }
