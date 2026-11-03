"""Read-only employee queries."""

from django.db.models import F, Q
from django.db.models.expressions import OrderBy
from django.db.models.functions import Lower

from common.pagination import paginate_queryset
from employees.models import Employee

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
    queryset = Employee.objects.select_related(
        "department",
        "job_title",
        "country",
        "manager",
    )

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
    if status != "all":
        queryset = queryset.filter(status=status)

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
