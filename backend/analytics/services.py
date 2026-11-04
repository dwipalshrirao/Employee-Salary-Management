"""Read-only analytics queries for the dashboard."""

from decimal import ROUND_HALF_UP, Decimal

from django.db import connection
from django.db.models import Count, Max, Min, Sum
from django.shortcuts import get_object_or_404

from analytics.bands import band_case, band_metadata
from employees.models import Employee
from employees.selectors import filter_employees

MEASURE_COLUMNS = {
    "total": "total_comp_cents",
    "base": "base_salary_cents",
}

GROUP_FIELDS = {
    "country": ("country_id", "country__name"),
    "department": ("department_id", "department__name"),
    "job_title": ("job_title_id", "job_title__name"),
}

DISTRIBUTION_GROUP_FIELDS = {
    "country": ("country_id", "country__name"),
    "department": ("department_id", "department__name"),
}

SORT_KEYS = {
    "headcount": "headcount",
    "total": "total_cents",
    "avg": "avg_cents",
    "min": "min_cents",
    "max": "max_cents",
}


def _measure_column(measure):
    try:
        return MEASURE_COLUMNS[measure]
    except KeyError as exc:
        raise ValueError(f"Unknown measure: {measure}") from exc


def _population(include_inactive):
    if include_inactive:
        return Employee.objects.all()
    return Employee.objects.filter(status=Employee.Status.ACTIVE)


def _scope(queryset, country_code=None, department_id=None, job_title_id=None):
    return filter_employees(
        queryset,
        country_code=country_code,
        department_id=department_id,
        job_title_id=job_title_id,
    )


def _average(total, headcount):
    if not headcount:
        return 0
    return int(
        (Decimal(total) / Decimal(headcount)).quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


def get_summary(
    *,
    measure="total",
    include_inactive=False,
    country_code=None,
    department_id=None,
    job_title_id=None,
):
    """Return the totals and component split for the selected population."""
    measure_column = _measure_column(measure)
    queryset = _scope(
        _population(include_inactive),
        country_code=country_code,
        department_id=department_id,
        job_title_id=job_title_id,
    )
    stats = queryset.aggregate(
        headcount=Count("id"),
        total_cents=Sum(measure_column),
        min_cents=Min(measure_column),
        max_cents=Max(measure_column),
        base_cents=Sum("base_salary_cents"),
        bonus_cents=Sum("bonus_cents"),
        allowances_cents=Sum("allowances_cents"),
        country_count=Count("country_id", distinct=True),
        department_count=Count("department_id", distinct=True),
    )
    headcount = stats["headcount"] or 0
    total_cents = stats["total_cents"] or 0
    return {
        "headcount": headcount,
        "total_cents": total_cents,
        "avg_cents": _average(total_cents, headcount),
        "min_cents": stats["min_cents"] or 0,
        "max_cents": stats["max_cents"] or 0,
        "components": {
            "base_cents": stats["base_cents"] or 0,
            "bonus_cents": stats["bonus_cents"] or 0,
            "allowances_cents": stats["allowances_cents"] or 0,
        },
        "country_count": stats["country_count"] or 0,
        "department_count": stats["department_count"] or 0,
    }


def _sort_rows(rows, sort_by, sort_dir):
    if sort_by == "name":
        rows.sort(key=lambda row: row["name"].casefold(), reverse=sort_dir == "desc")
        return
    value_key = SORT_KEYS[sort_by]
    rows.sort(key=lambda row: row["name"].casefold())
    rows.sort(key=lambda row: row[value_key], reverse=sort_dir == "desc")


def get_breakdown(
    *,
    group_by,
    measure="total",
    include_inactive=False,
    country_code=None,
    department_id=None,
    job_title_id=None,
    sort_by="avg",
    sort_dir="desc",
    limit=None,
):
    """Return grouped headcount and pay statistics for one dimension."""
    measure_column = _measure_column(measure)
    key_field, name_field = GROUP_FIELDS[group_by]
    queryset = _scope(
        _population(include_inactive),
        country_code=country_code,
        department_id=department_id,
        job_title_id=job_title_id,
    )
    grouped = queryset.values(key_field, name_field).annotate(
        headcount=Count("id"),
        total_cents=Sum(measure_column),
        min_cents=Min(measure_column),
        max_cents=Max(measure_column),
    )
    rows = [
        {
            "key": str(row[key_field]),
            "name": row[name_field],
            "headcount": row["headcount"],
            "total_cents": row["total_cents"] or 0,
            "avg_cents": _average(row["total_cents"] or 0, row["headcount"]),
            "min_cents": row["min_cents"] or 0,
            "max_cents": row["max_cents"] or 0,
        }
        for row in grouped
    ]
    _sort_rows(rows, sort_by, sort_dir)
    if limit is not None:
        rows = rows[:limit]
    return {
        "group_by": group_by,
        "measure": measure,
        "rows": rows,
    }


def get_distribution(
    *,
    group_by="none",
    measure="total",
    include_inactive=False,
    country_code=None,
    department_id=None,
    job_title_id=None,
):
    """Return salary-band counts for the selected population and grouping."""
    measure_column = _measure_column(measure)
    queryset = _scope(
        _population(include_inactive),
        country_code=country_code,
        department_id=department_id,
        job_title_id=job_title_id,
    )
    band_expression = band_case(measure_column)
    bands = band_metadata()

    if group_by == "none":
        rows = queryset.annotate(band=band_expression).values("band").annotate(count=Count("id"))
        counts = [0] * len(bands)
        headcount = 0
        for row in rows:
            counts[row["band"]] = row["count"]
            headcount += row["count"]
        groups = (
            [
                {
                    "key": "all",
                    "name": "All employees",
                    "headcount": headcount,
                    "counts": counts,
                }
            ]
            if headcount
            else []
        )
    else:
        key_field, name_field = DISTRIBUTION_GROUP_FIELDS[group_by]
        rows = (
            queryset.annotate(band=band_expression)
            .values(key_field, name_field, "band")
            .annotate(count=Count("id"))
        )
        grouped = {}
        for row in rows:
            key = str(row[key_field])
            group = grouped.setdefault(
                key,
                {
                    "key": key,
                    "name": row[name_field],
                    "headcount": 0,
                    "counts": [0] * len(bands),
                },
            )
            group["counts"][row["band"]] += row["count"]
            group["headcount"] += row["count"]
        groups = sorted(grouped.values(), key=lambda group: group["name"].casefold())

    return {
        "measure": measure,
        "bands": bands,
        "groups": groups,
    }


def get_team(
    manager_id,
    *,
    measure="total",
    include_inactive=False,
    country_code=None,
    department_id=None,
    job_title_id=None,
):
    """Return pay statistics for a manager's direct reports."""
    manager = get_object_or_404(
        Employee.objects.only("id", "full_name"),
        pk=manager_id,
    )
    measure_column = _measure_column(measure)
    queryset = _scope(
        _population(include_inactive).filter(manager_id=manager_id),
        country_code=country_code,
        department_id=department_id,
        job_title_id=job_title_id,
    )
    stats = queryset.aggregate(
        headcount=Count("id"),
        total_cents=Sum(measure_column),
        min_cents=Min(measure_column),
        max_cents=Max(measure_column),
    )
    headcount = stats["headcount"] or 0
    total_cents = stats["total_cents"] or 0
    return {
        "manager": {
            "id": manager.id,
            "full_name": manager.full_name,
        },
        "headcount": headcount,
        "total_cents": total_cents,
        "avg_cents": _average(total_cents, headcount),
        "min_cents": stats["min_cents"] or 0,
        "max_cents": stats["max_cents"] or 0,
    }


def _sql_scope_filters(
    alias,
    *,
    country_code=None,
    department_id=None,
    job_title_id=None,
):
    clauses = []
    params = []
    if country_code:
        clauses.append(f"{alias}.country_code = %s")
        params.append(country_code)
    if department_id is not None:
        clauses.append(f"{alias}.department_id = %s")
        params.append(department_id)
    if job_title_id is not None:
        clauses.append(f"{alias}.job_title_id = %s")
        params.append(job_title_id)
    return clauses, params


def get_outliers(
    *,
    threshold=Decimal("1.5"),
    min_peers=5,
    measure="total",
    country_code=None,
    department_id=None,
    job_title_id=None,
    page=1,
    page_size=25,
):
    """Return active employees paid above their peer-group threshold."""
    measure_column = _measure_column(measure)
    peer_scope, peer_scope_params = _sql_scope_filters(
        "employees",
        country_code=country_code,
        department_id=department_id,
        job_title_id=job_title_id,
    )
    outer_scope, outer_scope_params = _sql_scope_filters(
        "e",
        country_code=country_code,
        department_id=department_id,
        job_title_id=job_title_id,
    )
    peer_where = " AND ".join(["status = %s", *peer_scope])
    outer_where = " AND ".join(
        [
            "e.status = %s",
            f"e.{measure_column} > %s * p.total_m / p.n",
            *outer_scope,
        ]
    )
    peer_cte = f"""
        SELECT job_title_id, country_code,
               SUM({measure_column}) AS total_m,
               COUNT(*) AS n
        FROM employees
        WHERE {peer_where}
        GROUP BY job_title_id, country_code
        HAVING COUNT(*) >= %s
    """
    join_sql = """
        FROM employees e
        JOIN peer p
          ON p.job_title_id = e.job_title_id
         AND p.country_code = e.country_code
        JOIN job_titles jt ON jt.id = e.job_title_id
        JOIN countries c ON c.code = e.country_code
    """
    shared_params = [
        Employee.Status.ACTIVE,
        *peer_scope_params,
        min_peers,
        Employee.Status.ACTIVE,
        float(threshold),
        *outer_scope_params,
    ]
    count_sql = f"WITH peer AS ({peer_cte}) SELECT COUNT(*) {join_sql} WHERE {outer_where}"
    rows_sql = f"""
        WITH peer AS ({peer_cte})
        SELECT e.id, e.full_name, jt.name, c.name,
               e.{measure_column}, p.total_m, p.n,
               e.{measure_column} * 1.0 * p.n / p.total_m AS ratio
        {join_sql}
        WHERE {outer_where}
        ORDER BY ratio DESC, e.id
        LIMIT %s OFFSET %s
    """

    with connection.cursor() as cursor:
        cursor.execute(count_sql, shared_params)
        total = cursor.fetchone()[0]
        offset = (page - 1) * page_size
        cursor.execute(rows_sql, [*shared_params, page_size, offset])
        rows = cursor.fetchall()

    items = []
    for (
        employee_id,
        full_name,
        job_title,
        country,
        amount_cents,
        total_m,
        n,
        _sql_ratio,
    ) in rows:
        ratio = (Decimal(amount_cents) * Decimal(n) / Decimal(total_m)).quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
        items.append(
            {
                "employee_id": employee_id,
                "full_name": full_name,
                "job_title": job_title,
                "country": country,
                "amount_cents": amount_cents,
                "peer_avg_cents": _average(total_m, n),
                "ratio": float(ratio),
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }
