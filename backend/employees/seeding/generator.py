"""Build a deterministic, hierarchy-consistent employee seed.

The generator creates employees tier by tier so manager references always
point at a row inserted earlier. IDs are assigned explicitly, which keeps the
generated database identical for the same employee count and seed.
"""

import math
import random
import re
import unicodedata
from datetime import UTC, datetime, time, timedelta

from faker import Faker

from catalog.models import Department, JobTitle
from employees.models import Employee, SalaryHistory

from .reference import (
    COUNTRY_MIX,
    COUNTRY_MULTIPLIERS,
    DEPARTMENT_MIX,
    DEPARTMENT_MULTIPLIERS,
    EXECUTIVE_DEPARTMENT,
    FAKER_LOCALES,
    IC_TITLES,
    JOB_TITLES,
    LEVEL_BASE_SALARY,
    MANAGER_TITLES,
    NON_EXECUTIVE_DEPARTMENTS,
    SEED_NOW,
    SEED_TODAY,
)


def planned_tier_counts(total):
    """Return the required headcount for each level of the hierarchy."""
    if total < 25:
        raise ValueError("Seed at least 25 employees so every department has a manager.")

    directors = max(len(NON_EXECUTIVE_DEPARTMENTS), round(80 * total / 10_000))
    managers = max(len(NON_EXECUTIVE_DEPARTMENTS), round(700 * total / 10_000))
    individual_contributors = total - 1 - len(NON_EXECUTIVE_DEPARTMENTS) - directors - managers

    if individual_contributors < 0:
        raise ValueError("Employee count is too small for the required hierarchy.")

    return {
        "ceo": 1,
        "vp": len(NON_EXECUTIVE_DEPARTMENTS),
        "director": directors,
        "manager": managers,
        "individual_contributor": individual_contributors,
    }


def weighted_counts(total, weights):
    """Split ``total`` across keys using integer counts and remainder sorting."""
    weight_total = sum(weights.values())
    raw = {key: total * weight / weight_total for key, weight in weights.items()}
    counts = {key: int(value) for key, value in raw.items()}
    remaining = total - sum(counts.values())
    order = sorted(raw, key=lambda key: (raw[key] - counts[key], key), reverse=True)

    for index in range(remaining):
        counts[order[index % len(order)]] += 1

    return counts


def split_evenly(total, items):
    """Distribute ``total`` as evenly as possible across the provided items."""
    base, remainder = divmod(total, len(items))
    return {
        item: base + (1 if index < remainder else 0)
        for index, item in enumerate(items)
    }


def normalize_email_name(name):
    """Turn a display name into an ASCII-safe email local part."""
    ascii_name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-zA-Z0-9]+", ".", ascii_name).strip(".").lower()
    return slug or "employee"


class SeedGenerator:
    """Generate employees and salary history with stable IDs and dates."""

    def __init__(self, employee_count, seed):
        self.employee_count = employee_count
        self.seed = seed
        self.rng = random.Random(seed)
        self.tiers = planned_tier_counts(employee_count)
        self.next_id = 1
        self.employees = []
        self.history = []
        self.department_ids = {
            department.name: department.id for department in Department.objects.all()
        }
        self.job_title_ids = {
            job_title.name: job_title.id for job_title in JobTitle.objects.all()
        }
        self.fakers = {}
        for index, (country_code, locale) in enumerate(FAKER_LOCALES.items()):
            fake = Faker(locale)
            fake.seed_instance(seed + index)
            self.fakers[country_code] = fake

        # The CEO is explicitly US-based, so remove one US slot from the pool
        # used by everyone else and keep the final country mix exact.
        country_counts = weighted_counts(employee_count, COUNTRY_MIX)
        country_counts["US"] -= 1
        self.country_pool = [
            country_code
            for country_code, count in country_counts.items()
            for _ in range(count)
        ]
        self.rng.shuffle(self.country_pool)

    def build(self):
        """Build all tiers and return the employee and history objects."""
        self._build_ceo()
        self._build_vps()
        self._build_directors()
        self._build_managers()
        self._build_individual_contributors()
        return self.employees, self.history

    def _build_ceo(self):
        ceo = self._add_employee(
            department=EXECUTIVE_DEPARTMENT,
            job_title="Chief Executive Officer",
            country_code="US",
            manager=None,
            hire_date=SEED_TODAY.replace(year=2008, month=1, day=1),
        )
        self.ceo = ceo

    def _build_vps(self):
        self.vps = {}
        for department in NON_EXECUTIVE_DEPARTMENTS:
            vp = self._add_employee(
                department=department,
                job_title=f"VP of {department}",
                manager=self.ceo,
            )
            self.vps[department] = vp

    def _build_directors(self):
        self.directors = {department: [] for department in NON_EXECUTIVE_DEPARTMENTS}
        counts = split_evenly(self.tiers["director"], NON_EXECUTIVE_DEPARTMENTS)

        for department, count in counts.items():
            for _ in range(count):
                director = self._add_employee(
                    department=department,
                    job_title=f"Director of {department}",
                    manager=self.vps[department],
                )
                self.directors[department].append(director)

    def _build_managers(self):
        self.managers = {department: [] for department in NON_EXECUTIVE_DEPARTMENTS}
        counts = split_evenly(self.tiers["manager"], NON_EXECUTIVE_DEPARTMENTS)

        for department, count in counts.items():
            directors = self.directors[department]
            for index in range(count):
                manager = self._add_employee(
                    department=department,
                    job_title=MANAGER_TITLES[department],
                    manager=directors[index % len(directors)],
                )
                self.managers[department].append(manager)

    def _build_individual_contributors(self):
        individual_contributor_count = self.tiers["individual_contributor"]
        desired_department_counts = weighted_counts(
            self.employee_count - 1,
            DEPARTMENT_MIX,
        )
        leadership_counts = {
            department: 1 + len(self.directors[department]) + len(self.managers[department])
            for department in NON_EXECUTIVE_DEPARTMENTS
        }
        # Leaders (VP, director, manager) already contribute to each department.
        # Subtract them from the target so the final department mix stays close
        # to the spec for both 500-row and 10k-row seeds.
        if all(
            desired_department_counts[department] >= leadership_counts[department]
            for department in NON_EXECUTIVE_DEPARTMENTS
        ):
            department_counts = {
                department: desired_department_counts[department]
                - leadership_counts[department]
                for department in NON_EXECUTIVE_DEPARTMENTS
            }
        else:
            department_counts = weighted_counts(
                individual_contributor_count,
                DEPARTMENT_MIX,
            )
        # Outliers and inactive employees are chosen before generation so both
        # affect pay/history consistently and remain deterministic per seed.
        outlier_indices = set(
            self.rng.sample(
                range(individual_contributor_count),
                round(individual_contributor_count * 0.005),
            )
        )
        inactive_indices = set(
            self.rng.sample(
                range(individual_contributor_count),
                round(individual_contributor_count * 0.03),
            )
        )
        individual_contributor_index = 0

        for department, count in department_counts.items():
            managers = self.managers[department]
            for index in range(count):
                self._add_employee(
                    department=department,
                    job_title=self.rng.choice(IC_TITLES[department]),
                    manager=managers[index % len(managers)],
                    is_outlier=individual_contributor_index in outlier_indices,
                    is_inactive=individual_contributor_index in inactive_indices,
                )
                individual_contributor_index += 1

    def _add_employee(
        self,
        department,
        job_title,
        manager=None,
        country_code=None,
        hire_date=None,
        is_outlier=False,
        is_inactive=False,
    ):
        """Create one employee and its initial salary history row."""
        employee_id = self.next_id
        self.next_id += 1
        country_code = country_code or self.country_pool.pop()
        hire_date = hire_date or self._child_hire_date(manager.hire_date)
        full_name = self.fakers[country_code].name()
        email = f"{normalize_email_name(full_name)}.{employee_id}@acme.example"

        employee = Employee(
            id=employee_id,
            full_name=full_name,
            email=email,
            department_id=self.department_ids[department],
            job_title_id=self.job_title_ids[job_title],
            country_id=country_code,
            manager_id=manager.id if manager else None,
            hire_date=hire_date,
            status=(
                Employee.Status.INACTIVE
                if is_inactive
                else Employee.Status.ACTIVE
            ),
            created_at=SEED_NOW,
            updated_at=SEED_NOW,
        )
        self.employees.append(employee)
        self._add_history(employee, is_outlier=is_outlier)
        return employee

    def _child_hire_date(self, manager_hire_date):
        """Pick a hire date after the manager's, but before the seed date."""
        candidate = manager_hire_date + timedelta(
            days=self.rng.randint(180, 365 * 4)
        )
        latest = SEED_TODAY - timedelta(days=30)
        if candidate > latest:
            candidate = latest
        if candidate <= manager_hire_date:
            candidate = manager_hire_date + timedelta(days=30)
        return min(candidate, latest)

    def _add_history(self, employee, is_outlier=False):
        """Create a hire row and a deterministic chain of annual raises."""
        level = JOB_TITLES[self._job_title_name(employee.job_title_id)]
        base_cents, bonus_cents, allowances_cents, bonus_pct, allowance_pct = (
            self._initial_pay(employee, level, is_outlier=is_outlier)
        )
        hire_row = self._history_row(
            employee,
            employee.hire_date,
            "hire",
            "New hire",
            (base_cents, bonus_cents, allowances_cents),
            None,
        )
        rows = [hire_row]

        # Raises are bounded by full years of service and never exceed four.
        years = max(0, (SEED_TODAY - employee.hire_date).days // 365)
        raises = self.rng.randint(0, min(4, years))
        current = (base_cents, bonus_cents, allowances_cents)
        last_date = employee.hire_date

        for index in range(raises):
            effective_date = employee.hire_date + timedelta(
                days=365 * (index + 1) + self.rng.randint(0, 90)
            )
            if (effective_date - last_date).days < 180:
                effective_date = last_date + timedelta(days=180)
            if effective_date > SEED_TODAY:
                break

            new_base_dollars = max(
                1,
                round(
                    (current[0] / 100)
                    * (1 + self.rng.uniform(0.03, 0.10))
                ),
            )
            new_base = new_base_dollars * 100
            new_bonus = round(new_base_dollars * bonus_pct) * 100
            new_allowances = round(new_base_dollars * allowance_pct) * 100
            new = (new_base, new_bonus, new_allowances)
            rows.append(
                self._history_row(
                    employee,
                    effective_date,
                    "manual_edit",
                    "Annual review",
                    new,
                    current,
                )
            )
            current = new
            last_date = effective_date

        employee.base_salary_cents, employee.bonus_cents, employee.allowances_cents = current
        self.history.extend(rows)

    def _initial_pay(self, employee, level, is_outlier=False):
        """Return initial base, bonus and allowance cents plus percentages."""
        noise = math.exp(self.rng.gauss(0, 0.12))
        base_dollars = (
            LEVEL_BASE_SALARY[level]
            * COUNTRY_MULTIPLIERS[employee.country_id]
            * DEPARTMENT_MULTIPLIERS[self._department_name(employee.department_id)]
            * noise
        )
        if is_outlier:
            base_dollars *= self.rng.uniform(1.6, 2.2)
        base_dollars = max(1, round(base_dollars))

        if level <= 2:
            bonus_range = (0.0, 0.05)
        elif level <= 4:
            bonus_range = (0.05, 0.12)
        else:
            bonus_range = (0.10, 0.25)

        bonus_pct = self.rng.uniform(*bonus_range)
        allowance_pct = self.rng.uniform(0.02, 0.06)
        return (
            base_dollars * 100,
            round(base_dollars * bonus_pct) * 100,
            round(base_dollars * allowance_pct) * 100,
            bonus_pct,
            allowance_pct,
        )

    def _history_row(self, employee, effective_date, change_type, reason, new, previous):
        """Shape one append-only history row with previous values when present."""
        return SalaryHistory(
            employee_id=employee.id,
            effective_date=effective_date,
            change_type=change_type,
            reason=reason,
            batch_id=None,
            base_salary_cents=new[0],
            bonus_cents=new[1],
            allowances_cents=new[2],
            prev_base_salary_cents=previous[0] if previous else None,
            prev_bonus_cents=previous[1] if previous else None,
            prev_allowances_cents=previous[2] if previous else None,
            created_at=datetime.combine(effective_date, time(12), tzinfo=UTC),
        )

    def _department_name(self, department_id):
        """Resolve a department name once and cache it for the whole seed."""
        if not hasattr(self, "_department_names"):
            self._department_names = {
                department.id: department.name for department in Department.objects.all()
            }
        return self._department_names[department_id]

    def _job_title_name(self, job_title_id):
        """Resolve a job title name once and cache it for the whole seed."""
        if not hasattr(self, "_job_title_names"):
            self._job_title_names = {
                job_title.id: job_title.name for job_title in JobTitle.objects.all()
            }
        return self._job_title_names[job_title_id]
