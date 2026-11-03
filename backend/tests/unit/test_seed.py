import hashlib
import json
from collections import Counter

import pytest
from django.core.management import CommandError, call_command

from accounts.models import HrUser
from employees.models import Employee, SalaryHistory

pytestmark = pytest.mark.django_db(transaction=True)

SEED_ARGS = {"employees": 500, "seed": 42, "reset": True, "verify": True}


def database_checksum():
    digest = hashlib.sha256()

    employee_rows = Employee.objects.order_by("id").values(
        "id",
        "full_name",
        "email",
        "department_id",
        "job_title_id",
        "country_id",
        "manager_id",
        "hire_date",
        "status",
        "base_salary_cents",
        "bonus_cents",
        "allowances_cents",
        "total_comp_cents",
        "created_at",
        "updated_at",
    )
    for row in employee_rows:
        digest.update(json.dumps(row, sort_keys=True, default=str).encode())

    history_rows = SalaryHistory.objects.order_by("id").values(
        "id",
        "employee_id",
        "effective_date",
        "change_type",
        "reason",
        "batch_id",
        "base_salary_cents",
        "bonus_cents",
        "allowances_cents",
        "prev_base_salary_cents",
        "prev_bonus_cents",
        "prev_allowances_cents",
        "created_at",
    )
    for row in history_rows:
        digest.update(json.dumps(row, sort_keys=True, default=str).encode())

    return digest.hexdigest()


def test_seed_is_deterministic_and_passes_verify(capsys):
    call_command("seed", **SEED_ARGS)
    first_checksum = database_checksum()
    first_output = capsys.readouterr().out

    call_command("seed", **SEED_ARGS)
    second_checksum = database_checksum()
    second_output = capsys.readouterr().out

    assert first_checksum == second_checksum
    assert "verify" in first_output.lower()
    assert "verify" in second_output.lower()
    assert Employee.objects.count() == 500
    assert SalaryHistory.objects.count() >= 500
    assert HrUser.objects.count() == 1


def test_seed_verify_invariants_hold():
    call_command("seed", **SEED_ARGS)

    employees = {employee.id: employee for employee in Employee.objects.all()}
    latest_history = {}
    for row in SalaryHistory.objects.order_by("employee_id", "effective_date", "id"):
        latest_history[row.employee_id] = row

    assert len(latest_history) == len(employees)
    assert not Employee.objects.filter(manager__status=Employee.Status.INACTIVE).exists()
    assert not Employee.objects.filter(
        status=Employee.Status.INACTIVE,
        direct_reports__status=Employee.Status.ACTIVE,
    ).exists()

    for employee in employees.values():
        latest = latest_history[employee.id]
        assert employee.base_salary_cents == latest.base_salary_cents
        assert employee.bonus_cents == latest.bonus_cents
        assert employee.allowances_cents == latest.allowances_cents

        visited = set()
        current = employee
        while current.manager_id is not None:
            assert current.manager_id not in visited
            visited.add(current.id)
            current = employees[current.manager_id]

    titles = Counter(Employee.objects.values_list("job_title__name", flat=True))
    assert titles["Chief Executive Officer"] == 1
    assert sum(count for name, count in titles.items() if name.startswith("VP of ")) == 8


def test_seed_refuses_to_run_when_employees_exist_without_reset():
    call_command("seed", employees=100, seed=42, reset=True)

    with pytest.raises(CommandError, match="already"):
        call_command("seed", employees=100, seed=42)


def test_seed_verify_can_run_without_reseeding():
    call_command("seed", employees=100, seed=42, reset=True)
    before = database_checksum()

    call_command("seed", verify=True)

    assert database_checksum() == before
