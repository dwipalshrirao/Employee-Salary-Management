"""Invariant checks for a seeded database.

The verifier is intentionally read-only and reports every failed invariant in
one error so a bad seed is easy to diagnose.
"""

from collections import Counter

from django.core.management.base import CommandError

from employees.models import Employee, SalaryHistory

from .generator import planned_tier_counts
from .reference import (
    COUNTRY_MIX,
    DEPARTMENT_MIX,
    EXECUTIVE_DEPARTMENT,
    MANAGER_TITLES,
)


def verify_seed(stdout):
    """Raise ``CommandError`` if seeded distributions or relationships are bad."""
    employees = list(
        Employee.objects.select_related("department", "job_title").order_by("id")
    )
    if not employees:
        raise CommandError("Seed verification failed: there are no employees.")

    errors = []
    total = len(employees)

    # Allow a small tolerance for 500-row seeds; the 10k seed is exact.
    country_counts = Counter(employee.country_id for employee in employees)
    for country_code, target in COUNTRY_MIX.items():
        actual = country_counts[country_code] / total * 100
        if abs(actual - target) > 2:
            errors.append(
                f"country {country_code}: {actual:.1f}% (target {target}%)"
            )

    # The Executive department holds only the CEO, so exclude it from the mix.
    non_executive = [
        employee
        for employee in employees
        if employee.department.name != EXECUTIVE_DEPARTMENT
    ]
    non_executive_total = len(non_executive)
    if non_executive_total:
        department_counts = Counter(
            employee.department.name for employee in non_executive
        )
        for department, target in DEPARTMENT_MIX.items():
            actual = department_counts[department] / non_executive_total * 100
            if abs(actual - target) > 2:
                errors.append(
                    f"department {department}: {actual:.1f}% (target {target}%)"
                )

    try:
        planned = planned_tier_counts(total)
    except ValueError as exc:
        errors.append(str(exc))
        planned = None

    titles = Counter(employee.job_title.name for employee in employees)
    if planned:
        actual_tiers = {
            "ceo": titles["Chief Executive Officer"],
            "vp": sum(
                count
                for name, count in titles.items()
                if name.startswith("VP of ")
            ),
            "director": sum(
                count
                for name, count in titles.items()
                if name.startswith("Director of ")
            ),
            "manager": sum(titles[name] for name in MANAGER_TITLES.values()),
        }
        actual_tiers["individual_contributor"] = total - sum(actual_tiers.values())
        for tier, expected in planned.items():
            if actual_tiers[tier] != expected:
                errors.append(
                    f"{tier} count: {actual_tiers[tier]} (expected {expected})"
                )

    # Walk manager links for every employee; a repeated id means a cycle.
    employees_by_id = {employee.id: employee for employee in employees}
    for employee in employees:
        visited = set()
        current = employee
        while current.manager_id is not None:
            if current.id in visited:
                errors.append(f"cycle found at employee {employee.id}")
                break
            visited.add(current.id)
            current = employees_by_id[current.manager_id]
        if len(visited) > total:
            errors.append(f"cycle found at employee {employee.id}")
            break

    inactive_managers = Employee.objects.filter(
        manager__status=Employee.Status.INACTIVE
    ).count()
    if inactive_managers:
        errors.append(f"{inactive_managers} employees report to an inactive manager")

    inactive_with_active_reports = Employee.objects.filter(
        status=Employee.Status.INACTIVE,
        direct_reports__status=Employee.Status.ACTIVE,
    ).count()
    if inactive_with_active_reports:
        errors.append(
            f"{inactive_with_active_reports} inactive employees have active reports"
        )

    # Keep the last row per employee; the ordering matches "newest first".
    latest_history = {}
    history_count = 0
    for row in SalaryHistory.objects.order_by("employee_id", "effective_date", "id"):
        latest_history[row.employee_id] = row
        history_count += 1

    for employee in employees:
        latest = latest_history.get(employee.id)
        if latest is None:
            errors.append(f"employee {employee.id} has no salary history")
            continue
        if (
            employee.base_salary_cents,
            employee.bonus_cents,
            employee.allowances_cents,
        ) != (
            latest.base_salary_cents,
            latest.bonus_cents,
            latest.allowances_cents,
        ):
            errors.append(
                f"employee {employee.id} current pay does not match latest history"
            )

    if errors:
        raise CommandError(
            "Seed verification failed:\n" + "\n".join(f"- {error}" for error in errors)
        )

    stdout.write(
        "verify: "
        f"{total} employees, {history_count} history rows; "
        "country mix, department mix, tiers, cycles, manager status and "
        "current pay all passed."
    )
