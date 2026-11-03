"""Employee write services."""

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404

from common.clock import get_clock
from common.errors import ConflictError
from employees.models import Employee, SalaryHistory
from employees.services.hierarchy import validate_manager


def create_employee(data, clock=None):
    """Create an employee and its initial hire history row atomically."""
    clock = clock or get_clock()
    values = dict(data)
    manager = values.pop("manager", None)
    now = clock.now()

    try:
        with transaction.atomic():
            employee = Employee.objects.create(
                **values,
                manager=validate_manager(None, manager.id if manager else None),
                status=Employee.Status.ACTIVE,
                created_at=now,
                updated_at=now,
            )
            SalaryHistory.objects.create(
                employee=employee,
                effective_date=employee.hire_date,
                change_type=SalaryHistory.ChangeType.HIRE,
                reason="New hire",
                batch_id=None,
                base_salary_cents=employee.base_salary_cents,
                bonus_cents=employee.bonus_cents,
                allowances_cents=employee.allowances_cents,
                prev_base_salary_cents=None,
                prev_bonus_cents=None,
                prev_allowances_cents=None,
                created_at=now,
            )
    except IntegrityError as exc:
        raise ConflictError(
            "Email already exists",
            details={"field": "email"},
        ) from exc

    employee.direct_reports_count = 0
    return employee


def update_employee(employee_id, data, clock=None):
    """Apply a partial patch, writing history only when pay changes."""
    clock = clock or get_clock()
    values = dict(data)
    change_reason = (values.pop("change_reason", "") or "").strip() or "Manual edit"
    manager_supplied = "manager" in values
    manager = values.pop("manager", None)
    employee = get_object_or_404(Employee, pk=employee_id)
    previous_pay = (
        employee.base_salary_cents,
        employee.bonus_cents,
        employee.allowances_cents,
    )
    changed = False

    if manager_supplied:
        manager_id = manager.id if manager else None
        if employee.manager_id != manager_id:
            employee.manager = validate_manager(employee.id, manager_id)
            changed = True

    for field, value in values.items():
        if getattr(employee, field) != value:
            setattr(employee, field, value)
            changed = True

    if not changed:
        return employee

    now = clock.now()
    current_pay = (
        employee.base_salary_cents,
        employee.bonus_cents,
        employee.allowances_cents,
    )
    employee.updated_at = now

    try:
        with transaction.atomic():
            employee.save()
            if current_pay != previous_pay:
                SalaryHistory.objects.create(
                    employee=employee,
                    effective_date=clock.today(),
                    change_type=SalaryHistory.ChangeType.MANUAL_EDIT,
                    reason=change_reason,
                    batch_id=None,
                    base_salary_cents=employee.base_salary_cents,
                    bonus_cents=employee.bonus_cents,
                    allowances_cents=employee.allowances_cents,
                    prev_base_salary_cents=previous_pay[0],
                    prev_bonus_cents=previous_pay[1],
                    prev_allowances_cents=previous_pay[2],
                    created_at=now,
                )
    except IntegrityError as exc:
        raise ConflictError(
            "Email already exists",
            details={"field": "email"},
        ) from exc

    return employee
