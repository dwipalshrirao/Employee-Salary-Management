import pytest

from analytics.services import get_breakdown, get_summary
from tests.factories import make_analytics_dataset, make_department, make_employee

pytestmark = pytest.mark.django_db


def test_summary_matches_the_golden_totals():
    make_analytics_dataset()

    result = get_summary()

    assert result == {
        "headcount": 12,
        "total_cents": 96_300_000,
        "avg_cents": 8_025_000,
        "min_cents": 4_600_000,
        "max_cents": 13_800_000,
        "components": {
            "base_cents": 83_750_000,
            "bonus_cents": 8_375_000,
            "allowances_cents": 4_175_000,
        },
        "country_count": 3,
        "department_count": 3,
    }


def test_summary_measure_base_differs_from_total_with_the_same_headcount():
    make_analytics_dataset()

    result = get_summary(measure="base")

    assert result["headcount"] == 12
    assert result["total_cents"] == 83_750_000
    assert result["avg_cents"] == 6_979_167
    assert result["min_cents"] == 4_000_000
    assert result["max_cents"] == 12_000_000
    assert result["components"]["base_cents"] == 83_750_000


def test_summary_excludes_inactive_by_default_and_can_include_them():
    make_analytics_dataset()

    active = get_summary()
    including_inactive = get_summary(include_inactive=True)

    assert active["headcount"] == 12
    assert including_inactive["headcount"] == 14
    assert including_inactive["total_cents"] == 122_750_000
    assert including_inactive["avg_cents"] == 8_767_857
    assert including_inactive["min_cents"] == 3_450_000
    assert including_inactive["max_cents"] == 23_000_000
    assert including_inactive["components"] == {
        "base_cents": 106_750_000,
        "bonus_cents": 10_675_000,
        "allowances_cents": 5_325_000,
    }


def test_summary_scope_filters_and_empty_results():
    data = make_analytics_dataset()

    united_states = get_summary(country_code="US")
    engineering = get_summary(department_id=data["departments"]["engineering"].id)
    empty = get_summary(country_code="ZZ")

    assert united_states["headcount"] == 4
    assert united_states["total_cents"] == 42_550_000
    assert united_states["country_count"] == 1
    assert united_states["department_count"] == 3
    assert engineering["headcount"] == 6
    assert engineering["total_cents"] == 56_350_000
    assert empty == {
        "headcount": 0,
        "total_cents": 0,
        "avg_cents": 0,
        "min_cents": 0,
        "max_cents": 0,
        "components": {
            "base_cents": 0,
            "bonus_cents": 0,
            "allowances_cents": 0,
        },
        "country_count": 0,
        "department_count": 0,
    }


def test_averages_round_half_up_to_whole_cents():
    department = make_department("Rounding")
    make_employee(
        department=department,
        base_salary_cents=1,
        bonus_cents=0,
        allowances_cents=0,
    )
    make_employee(
        department=department,
        base_salary_cents=2,
        bonus_cents=0,
        allowances_cents=0,
    )

    result = get_summary(measure="base", department_id=department.id)

    assert result["total_cents"] == 3
    assert result["headcount"] == 2
    assert result["avg_cents"] == 2


def test_breakdown_by_country_defaults_to_average_descending():
    make_analytics_dataset()

    result = get_breakdown(group_by="country", measure="total")

    assert result["group_by"] == "country"
    assert result["measure"] == "total"
    assert [row["key"] for row in result["rows"]] == ["US", "DE", "IN"]
    assert result["rows"][0] == {
        "key": "US",
        "name": "United States",
        "headcount": 4,
        "total_cents": 42_550_000,
        "avg_cents": 10_637_500,
        "min_cents": 8_050_000,
        "max_cents": 13_800_000,
    }
    assert [row["avg_cents"] for row in result["rows"]] == [
        10_637_500,
        7_975_000,
        5_462_500,
    ]


def test_breakdown_by_department_sorts_limits_and_rounds():
    data = make_analytics_dataset()
    engineering_id = data["departments"]["engineering"].id
    sales_id = data["departments"]["sales"].id

    result = get_breakdown(group_by="department", measure="total", limit=2)
    all_rows = get_breakdown(group_by="department", measure="total")

    assert [row["key"] for row in result["rows"]] == [
        str(engineering_id),
        str(sales_id),
    ]
    assert [row["name"] for row in all_rows["rows"]] == [
        "Engineering",
        "Sales",
        "Finance",
    ]
    finance = all_rows["rows"][2]
    assert finance["headcount"] == 3
    assert finance["total_cents"] == 19_250_000
    assert finance["avg_cents"] == 6_416_667
    assert finance["min_cents"] == 5_175_000
    assert finance["max_cents"] == 8_050_000


def test_breakdown_by_job_title_returns_each_group():
    data = make_analytics_dataset()

    result = get_breakdown(group_by="job_title", measure="total")

    assert [row["name"] for row in result["rows"]] == [
        "Senior Engineer",
        "Software Engineer",
        "Account Executive",
        "Financial Analyst",
    ]
    assert result["rows"][0] == {
        "key": str(data["job_titles"]["senior_engineer"].id),
        "name": "Senior Engineer",
        "headcount": 2,
        "total_cents": 24_150_000,
        "avg_cents": 12_075_000,
        "min_cents": 10_350_000,
        "max_cents": 13_800_000,
    }


def test_breakdown_ties_break_by_name_ascending():
    make_analytics_dataset()

    result = get_breakdown(
        group_by="country",
        measure="total",
        sort_by="headcount",
        sort_dir="desc",
    )

    assert [row["name"] for row in result["rows"]] == [
        "Germany",
        "India",
        "United States",
    ]


def test_breakdown_scope_filters_and_empty_results():
    data = make_analytics_dataset()

    finance = get_breakdown(
        group_by="country",
        measure="base",
        department_id=data["departments"]["finance"].id,
        sort_by="name",
        sort_dir="asc",
    )
    empty = get_breakdown(group_by="country", country_code="ZZ")

    assert [row["key"] for row in finance["rows"]] == ["DE", "IN", "US"]
    assert [row["headcount"] for row in finance["rows"]] == [1, 1, 1]
    assert [row["total_cents"] for row in finance["rows"]] == [
        5_250_000,
        4_500_000,
        7_000_000,
    ]
    assert empty == {
        "group_by": "country",
        "measure": "total",
        "rows": [],
    }
