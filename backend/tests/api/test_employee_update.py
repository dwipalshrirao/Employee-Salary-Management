from datetime import date

import pytest

from employees.models import Employee, SalaryHistory
from tests.factories import make_employee

pytestmark = pytest.mark.django_db


def test_update_employee_requires_authentication(client):
    employee = make_employee()

    response = client.patch(
        f"/api/employees/{employee.id}",
        {"full_name": "Changed"},
        format="json",
    )

    assert response.status_code == 401


def test_pay_change_writes_one_manual_edit_history_row(auth_client, fixed_clock):
    employee = make_employee(
        full_name="Asha Patel",
        email="asha@acme.example",
        base_salary_cents=5_000_000,
        bonus_cents=500_000,
        allowances_cents=200_000,
    )

    response = auth_client.patch(
        f"/api/employees/{employee.id}",
        {
            "base_salary_cents": 5_250_000,
            "bonus_cents": 525_000,
            "change_reason": "Annual review",
        },
        format="json",
    )

    assert response.status_code == 200
    employee.refresh_from_db()
    assert employee.base_salary_cents == 5_250_000
    assert employee.bonus_cents == 525_000
    assert employee.total_comp_cents == 5_975_000
    history = SalaryHistory.objects.get(employee=employee)
    assert history.change_type == SalaryHistory.ChangeType.MANUAL_EDIT
    assert history.effective_date == date(2026, 10, 31)
    assert history.reason == "Annual review"
    assert history.base_salary_cents == 5_250_000
    assert history.bonus_cents == 525_000
    assert history.allowances_cents == 200_000
    assert history.prev_base_salary_cents == 5_000_000
    assert history.prev_bonus_cents == 500_000
    assert history.prev_allowances_cents == 200_000


def test_pay_change_without_reason_uses_manual_edit(auth_client):
    employee = make_employee(base_salary_cents=5_000_000)

    response = auth_client.patch(
        f"/api/employees/{employee.id}",
        {"base_salary_cents": 5_100_000},
        format="json",
    )

    assert response.status_code == 200
    assert SalaryHistory.objects.get(employee=employee).reason == "Manual edit"


def test_non_pay_change_does_not_write_history_and_keeps_manager(
    auth_client,
    fixed_clock,
):
    manager = make_employee(full_name="Manager", email="manager@acme.example")
    employee = make_employee(
        full_name="Asha Patel",
        email="asha@acme.example",
        manager=manager,
    )

    response = auth_client.patch(
        f"/api/employees/{employee.id}",
        {"full_name": "Asha Rao"},
        format="json",
    )

    assert response.status_code == 200
    employee.refresh_from_db()
    assert employee.full_name == "Asha Rao"
    assert employee.manager_id == manager.id
    assert employee.updated_at.isoformat() == "2026-10-31T12:00:00+00:00"
    assert SalaryHistory.objects.count() == 0


def test_no_op_patch_writes_nothing(auth_client):
    employee = make_employee(
        full_name="Asha Patel",
        base_salary_cents=5_000_000,
    )
    original_updated_at = employee.updated_at

    response = auth_client.patch(
        f"/api/employees/{employee.id}",
        {
            "full_name": "Asha Patel",
            "base_salary_cents": 5_000_000,
            "change_reason": "No change",
        },
        format="json",
    )

    assert response.status_code == 200
    employee.refresh_from_db()
    assert employee.updated_at == original_updated_at
    assert SalaryHistory.objects.count() == 0


def test_explicit_null_manager_removes_manager(auth_client):
    manager = make_employee(full_name="Manager", email="manager@acme.example")
    employee = make_employee(manager=manager)

    response = auth_client.patch(
        f"/api/employees/{employee.id}",
        {"manager_id": None},
        format="json",
    )

    assert response.status_code == 200
    employee.refresh_from_db()
    assert employee.manager is None
    assert SalaryHistory.objects.count() == 0


def test_update_rejects_inactive_manager(auth_client):
    inactive_manager = make_employee(
        email="inactive.manager@acme.example",
        status=Employee.Status.INACTIVE,
    )
    employee = make_employee()

    response = auth_client.patch(
        f"/api/employees/{employee.id}",
        {"manager_id": inactive_manager.id},
        format="json",
    )

    assert response.status_code == 422
    employee.refresh_from_db()
    assert employee.manager is None


def test_update_rejects_self_and_cycle(auth_client):
    manager = make_employee(full_name="Manager", email="manager@acme.example")
    employee = make_employee(
        full_name="Report",
        email="report@acme.example",
        manager=manager,
    )

    self_response = auth_client.patch(
        f"/api/employees/{employee.id}",
        {"manager_id": employee.id},
        format="json",
    )
    cycle_response = auth_client.patch(
        f"/api/employees/{manager.id}",
        {"manager_id": employee.id},
        format="json",
    )

    assert self_response.status_code == 422
    assert cycle_response.status_code == 422
    manager.refresh_from_db()
    assert manager.manager is None


def test_update_duplicate_email_returns_conflict(auth_client):
    make_employee(full_name="Existing", email="existing@acme.example")
    employee = make_employee(full_name="Target", email="target@acme.example")

    response = auth_client.patch(
        f"/api/employees/{employee.id}",
        {"email": "EXISTING@ACME.EXAMPLE"},
        format="json",
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    employee.refresh_from_db()
    assert employee.email == "target@acme.example"
    assert SalaryHistory.objects.count() == 0


@pytest.mark.parametrize(
    "patch",
    [
        {"department_id": 999999},
        {"status": "inactive"},
        {"total_comp_cents": 1},
        {"hire_date": "2026-11-01"},
        {"change_reason": "x" * 201},
    ],
)
def test_update_rejects_invalid_or_unknown_fields(
    auth_client,
    fixed_clock,
    patch,
):
    employee = make_employee()

    response = auth_client.patch(
        f"/api/employees/{employee.id}",
        patch,
        format="json",
    )

    assert response.status_code == 422
    assert SalaryHistory.objects.count() == 0


def test_update_unknown_employee_returns_404(auth_client):
    response = auth_client.patch(
        "/api/employees/999999",
        {"full_name": "Nobody"},
        format="json",
    )

    assert response.status_code == 404
