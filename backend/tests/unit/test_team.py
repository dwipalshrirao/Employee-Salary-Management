import pytest
from django.http import Http404

from analytics.services import get_team
from tests.factories import make_team_dataset

pytestmark = pytest.mark.django_db


def test_team_uses_two_queries(django_assert_num_queries):
    data = make_team_dataset()

    with django_assert_num_queries(2):
        get_team(data["manager"].id)


def test_team_counts_only_active_direct_reports():
    data = make_team_dataset()

    result = get_team(data["manager"].id)

    assert result == {
        "manager": {
            "id": data["manager"].id,
            "full_name": "Morgan Manager",
        },
        "headcount": 3,
        "total_cents": 60_000_000,
        "avg_cents": 20_000_000,
        "min_cents": 10_000_000,
        "max_cents": 30_000_000,
    }


def test_team_can_include_inactive_and_use_base_measure():
    data = make_team_dataset()

    result = get_team(
        data["manager"].id,
        measure="base",
        include_inactive=True,
    )

    assert result["headcount"] == 4
    assert result["total_cents"] == 80_000_000
    assert result["avg_cents"] == 20_000_000
    assert result["min_cents"] == 8_000_000
    assert result["max_cents"] == 32_000_000


def test_team_applies_scope_filters_to_direct_reports():
    data = make_team_dataset()

    result = get_team(data["manager"].id, country_code="US")

    assert result["headcount"] == 2
    assert result["total_cents"] == 30_000_000
    assert result["avg_cents"] == 15_000_000
    assert result["min_cents"] == 10_000_000
    assert result["max_cents"] == 20_000_000


def test_team_with_no_reports_returns_zero_stats():
    data = make_team_dataset()

    result = get_team(data["empty_manager"].id)

    assert result["headcount"] == 0
    assert result["total_cents"] == 0
    assert result["avg_cents"] == 0
    assert result["min_cents"] == 0
    assert result["max_cents"] == 0


def test_team_rounds_averages_half_up():
    data = make_team_dataset()
    reports = data["employees"]
    reports["report_one"].base_salary_cents = 1
    reports["report_one"].bonus_cents = 0
    reports["report_one"].save()
    reports["report_two"].base_salary_cents = 2
    reports["report_two"].bonus_cents = 0
    reports["report_two"].save()

    result = get_team(data["manager"].id, measure="base", country_code="US")

    assert result["total_cents"] == 3
    assert result["headcount"] == 2
    assert result["avg_cents"] == 2


def test_team_unknown_manager_raises_404():
    with pytest.raises(Http404):
        get_team(999_999)
