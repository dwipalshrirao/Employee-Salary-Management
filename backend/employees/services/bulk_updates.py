"""Bulk pay update preview and apply rules."""

from decimal import Decimal
from uuid import uuid4

from django.db import transaction
from django.db.models import BigIntegerField, Count, F, Max, Q, Sum
from django.db.models.functions import Cast, Round

from common.clock import get_clock
from common.errors import ResultTooLargeError, StaleCountError
from employees.models import Employee, SalaryHistory
from employees.selectors import filter_employees
from employees.serializers import MAX_AMOUNT_CENTS

COMPONENT_FIELDS = {
    "base": "base_salary_cents",
    "bonus": "bonus_cents",
    "allowances": "allowances_cents",
}


def _new_value_expression(component, mode, percentage, amount_cents):
    field = F(COMPONENT_FIELDS[component])
    if mode == "percent":
        basis_points = int(Decimal(str(percentage)) * 100)
        expression = Round(field * (10000 + basis_points) / 10000.0)
    else:
        expression = field + amount_cents
    return Cast(expression, BigIntegerField())


def _matching_queryset(data):
    component = data["component"]
    field = COMPONENT_FIELDS[component]
    expression = _new_value_expression(
        component,
        data["mode"],
        data.get("percentage"),
        data.get("amount_cents"),
    )
    filters = data.get("filter") or {}
    queryset = filter_employees(
        Employee.objects.all(),
        status=Employee.Status.ACTIVE,
        country_code=filters.get("country_code"),
        department_id=filters.get("department_id"),
        job_title_id=filters.get("job_title_id"),
        manager_id=filters.get("manager_id"),
    )
    queryset = queryset.annotate(new_value=expression).filter(
        ~Q(new_value=F(field))
    )
    return queryset, field, expression


def _aggregate(queryset, field):
    return queryset.aggregate(
        count=Count("id"),
        sum_before=Sum(field),
        sum_after=Sum("new_value"),
        max_new=Max("new_value"),
    )


def preview_bulk_update(data):
    """Return the affected count, sums and sample without changing anything."""
    queryset, field, _ = _matching_queryset(data)
    stats = _aggregate(queryset, field)
    max_new = stats["max_new"]
    if max_new is not None and max_new > MAX_AMOUNT_CENTS:
        raise ResultTooLargeError()

    sum_before = stats["sum_before"] or 0
    sum_after = stats["sum_after"] or 0
    sample = list(
        queryset.order_by("id").values(
            "id",
            "full_name",
            before_cents=F(field),
            after_cents=F("new_value"),
        )[:10]
    )
    return {
        "component": data["component"],
        "mode": data["mode"],
        "affected_count": stats["count"],
        "sum_before_cents": sum_before,
        "sum_after_cents": sum_after,
        "sum_delta_cents": sum_after - sum_before,
        "sample": sample,
    }


def apply_bulk_update(data, clock=None):
    """Apply a previewed bulk update in one transaction."""
    clock = clock or get_clock()
    expected_count = data["expected_count"]
    reason = data["reason"]

    with transaction.atomic():
        queryset, field, expression = _matching_queryset(data)
        stats = _aggregate(queryset, field)
        if stats["count"] != expected_count:
            raise StaleCountError("The data changed since the preview.")
        max_new = stats["max_new"]
        if max_new is not None and max_new > MAX_AMOUNT_CENTS:
            raise ResultTooLargeError()

        batch_id = uuid4()
        now = clock.now()
        today = clock.today()
        rows = list(
            queryset.order_by("id").values(
                "id",
                "base_salary_cents",
                "bonus_cents",
                "allowances_cents",
                "new_value",
            )
        )
        history_rows = []
        for row in rows:
            previous = {
                "base_salary_cents": row["base_salary_cents"],
                "bonus_cents": row["bonus_cents"],
                "allowances_cents": row["allowances_cents"],
            }
            current = dict(previous)
            current[field] = row["new_value"]
            history_rows.append(
                SalaryHistory(
                    employee_id=row["id"],
                    effective_date=today,
                    change_type=SalaryHistory.ChangeType.BULK_UPDATE,
                    reason=reason,
                    batch_id=batch_id,
                    base_salary_cents=current["base_salary_cents"],
                    bonus_cents=current["bonus_cents"],
                    allowances_cents=current["allowances_cents"],
                    prev_base_salary_cents=previous["base_salary_cents"],
                    prev_bonus_cents=previous["bonus_cents"],
                    prev_allowances_cents=previous["allowances_cents"],
                    created_at=now,
                )
            )

        SalaryHistory.objects.bulk_create(history_rows, batch_size=1_000)
        updated = queryset.update(**{field: expression, "updated_at": now})
        if updated != len(history_rows) or updated != expected_count:
            raise StaleCountError("The data changed since the preview.")

        sum_before = stats["sum_before"] or 0
        sum_after = stats["sum_after"] or 0
        return {
            "batch_id": str(batch_id),
            "component": data["component"],
            "affected_count": updated,
            "sum_delta_cents": sum_after - sum_before,
        }
