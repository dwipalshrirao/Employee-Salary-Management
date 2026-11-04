import pytest
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext

from analytics.services import get_team
from employees.models import Employee, SalaryHistory

pytestmark = pytest.mark.django_db


@pytest.fixture(scope="module")
def seeded(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        call_command("seed", employees=500, seed=42, reset=True, verbosity=0)

    yield

    with django_db_blocker.unblock():
        call_command("flush", interactive=False, verbosity=0)


def _plan(queryset):
    return queryset.explain()


def _plan_from_sql(sql):
    with connection.cursor() as cursor:
        cursor.execute(f"EXPLAIN QUERY PLAN {sql}")
        return "\n".join(row[-1] for row in cursor.fetchall())


def test_status_country_plan_uses_composite_index(seeded):
    country = Employee.objects.values_list("country_id", flat=True).first()

    plan = _plan(
        Employee.objects.filter(
            status=Employee.Status.ACTIVE,
            country_id=country,
        )
    )

    assert "idx_emp_status_country" in plan


def test_status_department_plan_uses_composite_index(seeded):
    department = Employee.objects.values_list("department_id", flat=True).first()

    plan = _plan(
        Employee.objects.filter(
            status=Employee.Status.ACTIVE,
            department_id=department,
        )
    )

    assert "idx_emp_status_dept" in plan


def test_manager_plan_uses_manager_index(seeded):
    manager_id = (
        Employee.objects.filter(direct_reports__isnull=False)
        .values_list("id", flat=True)
        .first()
    )

    plan = _plan(Employee.objects.filter(manager_id=manager_id))

    assert "idx_emp_manager" in plan


def test_employee_history_plan_uses_index_without_sort(seeded):
    employee_id = SalaryHistory.objects.values_list("employee_id", flat=True).first()

    plan = _plan(
        SalaryHistory.objects.filter(employee_id=employee_id).order_by(
            "-effective_date",
            "-id",
        )
    )

    assert "idx_history_employee_effective" in plan
    assert "TEMP B-TREE" not in plan


def test_default_history_plan_uses_index_without_sort(seeded):
    plan = _plan(SalaryHistory.objects.order_by("-effective_date", "-id"))

    assert "idx_history_effective" in plan
    assert "TEMP B-TREE" not in plan


def test_team_aggregate_uses_manager_index(seeded):
    manager_id = (
        Employee.objects.filter(direct_reports__isnull=False)
        .values_list("id", flat=True)
        .first()
    )

    with CaptureQueriesContext(connection) as captured:
        get_team(manager_id)

    assert len(captured) == 2
    assert "idx_emp_manager" in _plan_from_sql(captured.captured_queries[1]["sql"])
