"""Read-only employee queries."""

from django.db.models import Count, F, Q
from django.db.models.expressions import OrderBy
from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404

from common.pagination import paginate_queryset
from employees.models import Employee, SalaryHistory

SORT_FIELDS = {
    "full_name": Lower("full_name"),
    "email": Lower("email"),
    "hire_date": F("hire_date"),
    "base_salary": F("base_salary_cents"),
    "total_comp": F("total_comp_cents"),
    "department": Lower("department__name"),
    "job_title": Lower("job_title__name"),
    "country": Lower("country__name"),
}


def filter_employees(
    queryset,
    *,
    q=None,
    country_code=None,
    department_id=None,
    job_title_id=None,
    manager_id=None,
    status=None,
):
    """Apply the shared employee filters to a queryset."""
    if q:
        queryset = queryset.filter(
            Q(full_name__icontains=q) | Q(email__icontains=q)
        )
    if country_code:
        queryset = queryset.filter(country_id=country_code)
    if department_id is not None:
        queryset = queryset.filter(department_id=department_id)
    if job_title_id is not None:
        queryset = queryset.filter(job_title_id=job_title_id)
    if manager_id is not None:
        queryset = queryset.filter(manager_id=manager_id)
    if status and status != "all":
        queryset = queryset.filter(status=status)
    return queryset


def list_employees(
    *,
    q=None,
    country_code=None,
    department_id=None,
    job_title_id=None,
    manager_id=None,
    status="active",
    sort_by="full_name",
    sort_dir="asc",
    page=1,
    page_size=25,
):
    """Return a filtered, sorted page of employees and its total count."""
    queryset = filter_employees(
        Employee.objects.select_related(
            "department",
            "job_title",
            "country",
            "manager",
        ),
        q=q,
        country_code=country_code,
        department_id=department_id,
        job_title_id=job_title_id,
        manager_id=manager_id,
        status=status,
    )

    descending = sort_dir == "desc"
    queryset = queryset.order_by(
        OrderBy(SORT_FIELDS[sort_by], descending=descending),
        OrderBy(F("id"), descending=descending),
    )
    items, total = paginate_queryset(queryset, page, page_size)

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_employee_detail(employee_id):
    """Return one employee with lookups and a direct-report count."""
    return get_object_or_404(
        Employee.objects.select_related(
            "department",
            "job_title",
            "country__currency_code",
            "manager",
        ).annotate(direct_reports_count=Count("direct_reports")),
        pk=employee_id,
    )


def list_direct_reports(manager_id, page=1, page_size=25, status="all"):
    """Return a paginated list of an employee's direct reports."""
    get_object_or_404(Employee, pk=manager_id)
    queryset = Employee.objects.select_related(
        "department",
        "job_title",
        "country",
        "manager",
    ).filter(manager_id=manager_id)
    if status != "all":
        queryset = queryset.filter(status=status)
    queryset = queryset.order_by(
        OrderBy(Lower("full_name")),
        OrderBy(F("id")),
    )
    items, total = paginate_queryset(queryset, page, page_size)
    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def list_employee_history(employee_id):
    """Return one employee's salary history, newest first."""
    get_object_or_404(Employee, pk=employee_id)
    return list(
        SalaryHistory.objects.filter(employee_id=employee_id).order_by(
            "-effective_date",
            "-id",
        )
    )
