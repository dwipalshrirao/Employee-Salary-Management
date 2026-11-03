"""Employee write services."""

from django.db import IntegrityError, transaction

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
