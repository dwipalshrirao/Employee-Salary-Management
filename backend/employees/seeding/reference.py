"""Reference rows and distribution constants for the deterministic seed."""

from datetime import UTC, date, datetime

from catalog.models import Country, CurrencyRate, Department, JobTitle

# Fixed dates make history rows reproducible regardless of the wall clock.
SEED_TODAY = date(2026, 10, 1)
SEED_NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

CURRENCY_RATES = {
    "USD": 1.0,
    "INR": 83.0,
    "GBP": 0.79,
    "EUR": 0.92,
    "CAD": 1.36,
    "SGD": 1.34,
}

COUNTRIES = [
    ("IN", "India", "INR"),
    ("US", "United States", "USD"),
    ("GB", "United Kingdom", "GBP"),
    ("DE", "Germany", "EUR"),
    ("CA", "Canada", "CAD"),
    ("SG", "Singapore", "SGD"),
]

COUNTRY_CODES = [code for code, _, _ in COUNTRIES]

# Percentages from the seed spec; weighted_counts converts them to exact
# integer headcounts for any requested total.
COUNTRY_MIX = {
    "IN": 30,
    "US": 28,
    "GB": 12,
    "DE": 12,
    "CA": 9,
    "SG": 9,
}

FAKER_LOCALES = {
    "IN": "en_IN",
    "US": "en_US",
    "GB": "en_GB",
    "DE": "de_DE",
    "CA": "en_CA",
    "SG": "en_US",
}

EXECUTIVE_DEPARTMENT = "Executive"

DEPARTMENTS = [
    EXECUTIVE_DEPARTMENT,
    "Engineering",
    "Product",
    "Sales",
    "Marketing",
    "Customer Support",
    "Finance",
    "Human Resources",
    "Operations",
]

NON_EXECUTIVE_DEPARTMENTS = [
    "Engineering",
    "Product",
    "Sales",
    "Marketing",
    "Customer Support",
    "Finance",
    "Human Resources",
    "Operations",
]

# Non-executive mix; the Executive department only contains the CEO.
DEPARTMENT_MIX = {
    "Engineering": 30,
    "Sales": 18,
    "Customer Support": 14,
    "Operations": 10,
    "Marketing": 8,
    "Product": 8,
    "Finance": 7,
    "Human Resources": 5,
}

JOB_TITLES = {
    "Chief Executive Officer": 7,
    "VP of Engineering": 6,
    "VP of Product": 6,
    "VP of Sales": 6,
    "VP of Marketing": 6,
    "VP of Customer Support": 6,
    "VP of Finance": 6,
    "VP of Human Resources": 6,
    "VP of Operations": 6,
    "Director of Engineering": 5,
    "Director of Product": 5,
    "Director of Sales": 5,
    "Director of Marketing": 5,
    "Director of Customer Support": 5,
    "Director of Finance": 5,
    "Director of Human Resources": 5,
    "Director of Operations": 5,
    "Engineering Manager": 4,
    "Group Product Manager": 4,
    "Sales Manager": 4,
    "Marketing Manager": 4,
    "Support Team Lead": 4,
    "Finance Manager": 4,
    "HR Manager": 4,
    "Operations Manager": 4,
    "Software Engineer": 2,
    "Senior Software Engineer": 3,
    "Staff Engineer": 4,
    "Associate Product Manager": 2,
    "Product Manager": 3,
    "Senior Product Manager": 4,
    "Sales Development Rep": 1,
    "Account Executive": 2,
    "Senior Account Executive": 3,
    "Marketing Associate": 1,
    "Marketing Specialist": 2,
    "Senior Marketing Specialist": 3,
    "Support Specialist": 1,
    "Senior Support Specialist": 2,
    "Financial Analyst": 2,
    "Senior Financial Analyst": 3,
    "HR Associate": 1,
    "HR Business Partner": 3,
    "Operations Associate": 1,
    "Operations Analyst": 2,
    "Senior Operations Analyst": 3,
}

MANAGER_TITLES = {
    "Engineering": "Engineering Manager",
    "Product": "Group Product Manager",
    "Sales": "Sales Manager",
    "Marketing": "Marketing Manager",
    "Customer Support": "Support Team Lead",
    "Finance": "Finance Manager",
    "Human Resources": "HR Manager",
    "Operations": "Operations Manager",
}

IC_TITLES = {
    "Engineering": ["Software Engineer", "Senior Software Engineer", "Staff Engineer"],
    "Product": ["Associate Product Manager", "Product Manager", "Senior Product Manager"],
    "Sales": ["Sales Development Rep", "Account Executive", "Senior Account Executive"],
    "Marketing": ["Marketing Associate", "Marketing Specialist", "Senior Marketing Specialist"],
    "Customer Support": ["Support Specialist", "Senior Support Specialist"],
    "Finance": ["Financial Analyst", "Senior Financial Analyst"],
    "Human Resources": ["HR Associate", "HR Business Partner"],
    "Operations": ["Operations Associate", "Operations Analyst", "Senior Operations Analyst"],
}

COUNTRY_MULTIPLIERS = {
    "US": 1.00,
    "SG": 0.85,
    "CA": 0.82,
    "DE": 0.80,
    "GB": 0.78,
    "IN": 0.32,
}

DEPARTMENT_MULTIPLIERS = {
    "Executive": 1.00,
    "Engineering": 1.10,
    "Product": 1.05,
    "Sales": 1.00,
    "Finance": 1.00,
    "Marketing": 0.95,
    "Human Resources": 0.90,
    "Operations": 0.88,
    "Customer Support": 0.80,
}

LEVEL_BASE_SALARY = {
    1: 45_000,
    2: 65_000,
    3: 90_000,
    4: 120_000,
    5: 160_000,
    6: 220_000,
    7: 350_000,
}


def create_reference_data():
    """Insert lookup data with conflict-safe bulk inserts for repeatable seeds."""
    CurrencyRate.objects.bulk_create(
        [
            CurrencyRate(
                currency_code=code,
                rate_per_usd=rate,
                updated_at=SEED_NOW,
            )
            for code, rate in CURRENCY_RATES.items()
        ],
        ignore_conflicts=True,
    )
    Country.objects.bulk_create(
        [
            Country(
                code=code,
                name=name,
                currency_code_id=currency_code,
            )
            for code, name, currency_code in COUNTRIES
        ],
        ignore_conflicts=True,
    )
    Department.objects.bulk_create(
        [Department(name=name) for name in DEPARTMENTS],
        ignore_conflicts=True,
    )
    JobTitle.objects.bulk_create(
        [JobTitle(name=name, level=level) for name, level in JOB_TITLES.items()],
        ignore_conflicts=True,
    )
