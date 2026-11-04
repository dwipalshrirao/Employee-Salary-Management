"""Small factories for readable employee API tests."""

from datetime import UTC, date, datetime
from itertools import count

from catalog.models import Country, CurrencyRate, Department, JobTitle
from employees.models import Employee, SalaryHistory

DEFAULT_NOW = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
_employee_ids = count(1)


def make_currency_rate(code="USD", rate_per_usd=1.0):
    return CurrencyRate.objects.get_or_create(
        currency_code=code,
        defaults={"rate_per_usd": rate_per_usd, "updated_at": DEFAULT_NOW},
    )[0]


def make_country(code="US", name="United States", currency_code="USD"):
    make_currency_rate(currency_code)
    return Country.objects.get_or_create(
        code=code,
        defaults={"name": name, "currency_code_id": currency_code},
    )[0]


def make_department(name="Engineering"):
    return Department.objects.get_or_create(name=name)[0]


def make_job_title(name="Software Engineer", level=2):
    return JobTitle.objects.get_or_create(name=name, defaults={"level": level})[0]


def make_employee(**overrides):
    index = next(_employee_ids)
    data = {
        "full_name": f"Employee {index}",
        "email": f"employee{index}@acme.example",
        "department": make_department(),
        "job_title": make_job_title(),
        "country": make_country(),
        "manager": None,
        "hire_date": date(2021, 1, 1),
        "status": Employee.Status.ACTIVE,
        "base_salary_cents": 5_000_000,
        "bonus_cents": 500_000,
        "allowances_cents": 200_000,
        "created_at": DEFAULT_NOW,
        "updated_at": DEFAULT_NOW,
    }
    data.update(overrides)
    return Employee.objects.create(**data)


def make_salary_history(**overrides):
    data = {
        "employee": overrides.pop("employee", None) or make_employee(),
        "effective_date": date(2026, 1, 1),
        "change_type": SalaryHistory.ChangeType.HIRE,
        "reason": "New hire",
        "batch_id": None,
        "base_salary_cents": 5_000_000,
        "bonus_cents": 500_000,
        "allowances_cents": 200_000,
        "prev_base_salary_cents": None,
        "prev_bonus_cents": None,
        "prev_allowances_cents": None,
        "created_at": DEFAULT_NOW,
    }
    data.update(overrides)
    return SalaryHistory.objects.create(**data)


def make_analytics_dataset():
    """Build the fixed 14-employee analytics golden dataset."""
    countries = {
        "US": make_country("US", "United States", "USD"),
        "IN": make_country("IN", "India", "INR"),
        "DE": make_country("DE", "Germany", "EUR"),
    }
    departments = {
        "engineering": make_department("Engineering"),
        "sales": make_department("Sales"),
        "finance": make_department("Finance"),
    }
    job_titles = {
        "software_engineer": make_job_title("Software Engineer", 2),
        "senior_engineer": make_job_title("Senior Engineer", 3),
        "account_executive": make_job_title("Account Executive", 2),
        "financial_analyst": make_job_title("Financial Analyst", 2),
    }
    specs = [
        (
            "asha_patel",
            "Asha Patel",
            "US",
            "engineering",
            "software_engineer",
            10_000_000,
            1_000_000,
            500_000,
            Employee.Status.ACTIVE,
        ),
        (
            "ben_carter",
            "Ben Carter",
            "US",
            "engineering",
            "senior_engineer",
            12_000_000,
            1_200_000,
            600_000,
            Employee.Status.ACTIVE,
        ),
        (
            "chloe_diaz",
            "Chloe Diaz",
            "US",
            "sales",
            "account_executive",
            8_000_000,
            800_000,
            400_000,
            Employee.Status.ACTIVE,
        ),
        (
            "dan_evans",
            "Dan Evans",
            "US",
            "finance",
            "financial_analyst",
            7_000_000,
            700_000,
            350_000,
            Employee.Status.ACTIVE,
        ),
        (
            "priya_nair",
            "Priya Nair",
            "IN",
            "engineering",
            "software_engineer",
            5_000_000,
            500_000,
            250_000,
            Employee.Status.ACTIVE,
        ),
        (
            "ravi_shah",
            "Ravi Shah",
            "IN",
            "engineering",
            "software_engineer",
            5_500_000,
            550_000,
            275_000,
            Employee.Status.ACTIVE,
        ),
        (
            "sana_khan",
            "Sana Khan",
            "IN",
            "sales",
            "account_executive",
            4_000_000,
            400_000,
            200_000,
            Employee.Status.ACTIVE,
        ),
        (
            "vikram_rao",
            "Vikram Rao",
            "IN",
            "finance",
            "financial_analyst",
            4_500_000,
            450_000,
            225_000,
            Employee.Status.ACTIVE,
        ),
        (
            "lukas_meyer",
            "Lukas Meyer",
            "DE",
            "engineering",
            "senior_engineer",
            9_000_000,
            900_000,
            450_000,
            Employee.Status.ACTIVE,
        ),
        (
            "mia_schmidt",
            "Mia Schmidt",
            "DE",
            "sales",
            "account_executive",
            6_000_000,
            600_000,
            300_000,
            Employee.Status.ACTIVE,
        ),
        (
            "noah_wagner",
            "Noah Wagner",
            "DE",
            "finance",
            "financial_analyst",
            5_250_000,
            525_000,
            250_000,
            Employee.Status.ACTIVE,
        ),
        (
            "emma_wolf",
            "Emma Wolf",
            "DE",
            "engineering",
            "software_engineer",
            7_500_000,
            750_000,
            375_000,
            Employee.Status.ACTIVE,
        ),
        (
            "zara_ali",
            "Zara Ali",
            "US",
            "engineering",
            "senior_engineer",
            20_000_000,
            2_000_000,
            1_000_000,
            Employee.Status.INACTIVE,
        ),
        (
            "omar_hassan",
            "Omar Hassan",
            "IN",
            "sales",
            "account_executive",
            3_000_000,
            300_000,
            150_000,
            Employee.Status.INACTIVE,
        ),
    ]
    employees = {}
    for (
        key,
        name,
        country_code,
        department_key,
        title_key,
        base_salary_cents,
        bonus_cents,
        allowances_cents,
        status,
    ) in specs:
        employees[key] = make_employee(
            full_name=name,
            email=f"{key}@acme.example",
            country=countries[country_code],
            department=departments[department_key],
            job_title=job_titles[title_key],
            status=status,
            base_salary_cents=base_salary_cents,
            bonus_cents=bonus_cents,
            allowances_cents=allowances_cents,
        )
    return {
        "countries": countries,
        "departments": departments,
        "job_titles": job_titles,
        "employees": employees,
    }
