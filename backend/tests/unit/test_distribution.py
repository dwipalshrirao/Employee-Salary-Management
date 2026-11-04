import pytest

from analytics.bands import BANDS
from analytics.services import get_distribution
from tests.factories import (
    make_analytics_dataset,
    make_country,
    make_department,
    make_employee,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def edge_dataset():
    engineering = make_department("Engineering")
    sales = make_department("Sales")
    finance = make_department("Finance")
    employees = {}
    specs = [
        ("below", 2_999_999, engineering),
        ("thirty", 3_000_000, engineering),
        ("forty_nine", 4_999_999, engineering),
        ("fifty", 5_000_000, sales),
        ("seventy_four", 7_499_999, sales),
        ("seventy_five", 7_500_000, sales),
        ("one_hundred", 10_000_000, finance),
        ("one_fifty", 15_000_000, finance),
        ("two_hundred", 20_000_000, finance),
        ("above_two_hundred", 20_000_001, finance),
    ]
    for key, base_salary_cents, department in specs:
        employees[key] = make_employee(
            full_name=f"Edge {key}",
            email=f"edge-{key}@acme.example",
            department=department,
            base_salary_cents=base_salary_cents,
            bonus_cents=0,
            allowances_cents=0,
        )
    return employees


def test_bands_are_defined_once_with_the_expected_edges_and_labels():
    assert [band["index"] for band in BANDS] == list(range(7))
    assert [band["upper_bound"] for band in BANDS] == [
        3_000_000,
        5_000_000,
        7_500_000,
        10_000_000,
        15_000_000,
        20_000_000,
        None,
    ]
    assert [band["label"] for band in BANDS] == [
        "< $30k",
        "$30k - $50k",
        "$50k - $75k",
        "$75k - $100k",
        "$100k - $150k",
        "$150k - $200k",
        "$200k+",
    ]


def test_distribution_puts_edge_values_in_the_higher_band(edge_dataset):
    result = get_distribution(measure="base")

    assert result["measure"] == "base"
    assert result["bands"] == [
        {"index": 0, "label": "< $30k"},
        {"index": 1, "label": "$30k - $50k"},
        {"index": 2, "label": "$50k - $75k"},
        {"index": 3, "label": "$75k - $100k"},
        {"index": 4, "label": "$100k - $150k"},
        {"index": 5, "label": "$150k - $200k"},
        {"index": 6, "label": "$200k+"},
    ]
    assert result["groups"] == [
        {
            "key": "all",
            "name": "All employees",
            "headcount": 10,
            "counts": [1, 2, 2, 1, 1, 1, 2],
        }
    ]


def test_distribution_groups_have_zero_filled_bands_and_matching_headcounts():
    engineering = make_department("Engineering")
    sales = make_department("Sales")
    finance = make_department("Finance")
    make_employee(
        full_name="Engineer",
        department=engineering,
        base_salary_cents=3_000_000,
        bonus_cents=0,
        allowances_cents=0,
    )
    make_employee(
        full_name="Seller",
        department=sales,
        base_salary_cents=7_500_000,
        bonus_cents=0,
        allowances_cents=0,
    )
    make_employee(
        full_name="Analyst",
        department=finance,
        base_salary_cents=20_000_000,
        bonus_cents=0,
        allowances_cents=0,
    )

    result = get_distribution(group_by="department", measure="base")

    groups = {group["name"]: group for group in result["groups"]}
    assert [group["name"] for group in result["groups"]] == [
        "Engineering",
        "Finance",
        "Sales",
    ]
    assert groups["Engineering"]["counts"] == [0, 1, 0, 0, 0, 0, 0]
    assert groups["Finance"]["counts"] == [0, 0, 0, 0, 0, 0, 1]
    assert groups["Sales"]["counts"] == [0, 0, 0, 1, 0, 0, 0]
    for group in result["groups"]:
        assert len(group["counts"]) == 7
        assert sum(group["counts"]) == group["headcount"]


def test_distribution_by_country_and_scope_filters():
    data = make_analytics_dataset()

    result = get_distribution(
        group_by="country",
        department_id=data["departments"]["finance"].id,
    )

    groups = {group["key"]: group for group in result["groups"]}
    assert [group["key"] for group in result["groups"]] == ["DE", "IN", "US"]
    assert groups["US"]["headcount"] == 1
    assert groups["IN"]["headcount"] == 1
    assert groups["DE"]["headcount"] == 1
    assert groups["US"]["counts"] == [0, 0, 0, 1, 0, 0, 0]
    assert groups["IN"]["counts"] == [0, 0, 1, 0, 0, 0, 0]
    assert groups["DE"]["counts"] == [0, 0, 1, 0, 0, 0, 0]


def test_distribution_includes_inactive_only_when_requested():
    country = make_country("US", "United States", "USD")
    department = make_department("Inactive")
    make_employee(
        full_name="Inactive Person",
        email="inactive-analytics@acme.example",
        country=country,
        department=department,
        status="inactive",
        base_salary_cents=25_000_000,
        bonus_cents=0,
        allowances_cents=0,
    )

    active = get_distribution(measure="base")
    including_inactive = get_distribution(measure="base", include_inactive=True)

    assert active["groups"] == []
    assert including_inactive["groups"][0]["counts"] == [0, 0, 0, 0, 0, 0, 1]
    assert including_inactive["groups"][0]["headcount"] == 1


def test_distribution_empty_scope_returns_bands_and_no_groups():
    result = get_distribution(country_code="ZZ")

    assert len(result["bands"]) == 7
    assert result["groups"] == []
