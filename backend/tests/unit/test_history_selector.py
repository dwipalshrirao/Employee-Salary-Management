from datetime import date
from uuid import uuid4

import pytest

from employees.models import Employee, SalaryHistory
from employees.selectors import list_salary_history
from tests.factories import make_employee, make_salary_history

pytestmark = pytest.mark.django_db


@pytest.fixture
def history_data():
    asha = make_employee(
        full_name="Asha Patel",
        email="asha@acme.example",
    )
    john = make_employee(
        full_name="John Smith",
        email="john@acme.example",
        status=Employee.Status.INACTIVE,
    )
    percent = make_employee(
        full_name="100% Match",
        email="percent@acme.example",
    )
    underscore = make_employee(
        full_name="Under_score",
        email="under_score@acme.example",
    )
    batch_id = uuid4()

    hire = make_salary_history(
        employee=asha,
        effective_date=date(2021, 6, 1),
        change_type=SalaryHistory.ChangeType.HIRE,
        reason="New hire",
        base_salary_cents=4_000_000,
        bonus_cents=400_000,
        allowances_cents=100_000,
    )
    review = make_salary_history(
        employee=asha,
        effective_date=date(2024, 6, 1),
        change_type=SalaryHistory.ChangeType.MANUAL_EDIT,
        reason="Annual review",
        base_salary_cents=4_500_000,
        bonus_cents=450_000,
        allowances_cents=150_000,
        prev_base_salary_cents=hire.base_salary_cents,
        prev_bonus_cents=hire.bonus_cents,
        prev_allowances_cents=hire.allowances_cents,
    )
    asha_bulk = make_salary_history(
        employee=asha,
        effective_date=date(2026, 1, 1),
        change_type=SalaryHistory.ChangeType.BULK_UPDATE,
        reason="FY27 raise",
        batch_id=batch_id,
        base_salary_cents=5_000_000,
        bonus_cents=500_000,
        allowances_cents=200_000,
        prev_base_salary_cents=review.base_salary_cents,
        prev_bonus_cents=review.bonus_cents,
        prev_allowances_cents=review.allowances_cents,
    )
    john_bulk = make_salary_history(
        employee=john,
        effective_date=date(2026, 1, 1),
        change_type=SalaryHistory.ChangeType.BULK_UPDATE,
        reason="FY27 raise",
        batch_id=batch_id,
        base_salary_cents=6_000_000,
        bonus_cents=600_000,
        allowances_cents=240_000,
        prev_base_salary_cents=5_500_000,
        prev_bonus_cents=550_000,
        prev_allowances_cents=220_000,
    )
    percent_row = make_salary_history(
        employee=percent,
        effective_date=date(2026, 2, 1),
        change_type=SalaryHistory.ChangeType.MANUAL_EDIT,
        reason="100% bonus",
    )
    underscore_row = make_salary_history(
        employee=underscore,
        effective_date=date(2026, 2, 2),
        change_type=SalaryHistory.ChangeType.MANUAL_EDIT,
        reason="under_score",
    )
    return {
        "asha": asha,
        "john": john,
        "hire": hire,
        "review": review,
        "asha_bulk": asha_bulk,
        "john_bulk": john_bulk,
        "percent_row": percent_row,
        "underscore_row": underscore_row,
        "batch_id": batch_id,
    }


def test_search_returns_newest_first_and_includes_inactive_employees(history_data):
    result = list_salary_history()

    assert result["total"] == 6
    assert [row.id for row in result["items"]] == [
        history_data["underscore_row"].id,
        history_data["percent_row"].id,
        history_data["john_bulk"].id,
        history_data["asha_bulk"].id,
        history_data["review"].id,
        history_data["hire"].id,
    ]
    assert history_data["john"].id in {row.employee_id for row in result["items"]}


def test_employee_filter_matches_name_or_email(history_data):
    by_name = list_salary_history(employee="asha")
    by_email = list_salary_history(employee="JOHN@ACME")

    assert by_name["total"] == 3
    assert {row.employee_id for row in by_name["items"]} == {history_data["asha"].id}
    assert [row.id for row in by_email["items"]] == [history_data["john_bulk"].id]


def test_reason_and_change_type_filters(history_data):
    by_reason = list_salary_history(reason="fy27")
    by_type = list_salary_history(change_type=SalaryHistory.ChangeType.HIRE)

    assert {row.id for row in by_reason["items"]} == {
        history_data["asha_bulk"].id,
        history_data["john_bulk"].id,
    }
    assert [row.id for row in by_type["items"]] == [history_data["hire"].id]


def test_date_range_is_inclusive_on_both_ends(history_data):
    result = list_salary_history(
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 1),
    )

    assert result["total"] == 2
    assert {row.id for row in result["items"]} == {
        history_data["asha_bulk"].id,
        history_data["john_bulk"].id,
    }


def test_batch_filter_returns_every_row_in_the_batch(history_data):
    result = list_salary_history(batch_id=history_data["batch_id"])

    assert result["total"] == 2
    assert {row.id for row in result["items"]} == {
        history_data["asha_bulk"].id,
        history_data["john_bulk"].id,
    }


def test_filters_combine(history_data):
    result = list_salary_history(
        employee="asha",
        reason="FY27",
        change_type=SalaryHistory.ChangeType.BULK_UPDATE,
        date_from=date(2026, 1, 1),
        date_to=date(2026, 1, 1),
        batch_id=history_data["batch_id"],
    )

    assert result["total"] == 1
    assert [row.id for row in result["items"]] == [history_data["asha_bulk"].id]


def test_percent_and_underscore_in_search_text_are_literal(history_data):
    percent_reason = list_salary_history(reason="%")
    underscore_reason = list_salary_history(reason="_")
    percent_employee = list_salary_history(employee="%")
    underscore_employee = list_salary_history(employee="_")

    assert [row.id for row in percent_reason["items"]] == [
        history_data["percent_row"].id
    ]
    assert [row.id for row in underscore_reason["items"]] == [
        history_data["underscore_row"].id
    ]
    assert [row.id for row in percent_employee["items"]] == [
        history_data["percent_row"].id
    ]
    assert [row.id for row in underscore_employee["items"]] == [
        history_data["underscore_row"].id
    ]


def test_sort_by_employee_uses_name_and_id_tiebreaker(history_data):
    ascending = list_salary_history(sort_by="employee", sort_dir="asc")
    descending = list_salary_history(sort_by="employee", sort_dir="desc")

    assert [row.employee.full_name for row in ascending["items"]] == [
        "100% Match",
        "Asha Patel",
        "Asha Patel",
        "Asha Patel",
        "John Smith",
        "Under_score",
    ]
    assert [row.employee.full_name for row in descending["items"]] == [
        "Under_score",
        "John Smith",
        "Asha Patel",
        "Asha Patel",
        "Asha Patel",
        "100% Match",
    ]
    assert [row.id for row in ascending["items"]] == [
        history_data["percent_row"].id,
        history_data["hire"].id,
        history_data["review"].id,
        history_data["asha_bulk"].id,
        history_data["john_bulk"].id,
        history_data["underscore_row"].id,
    ]


def test_sort_by_change_type(history_data):
    ascending = list_salary_history(sort_by="change_type", sort_dir="asc")
    descending = list_salary_history(sort_by="change_type", sort_dir="desc")

    assert [row.change_type for row in ascending["items"]] == [
        "bulk_update",
        "bulk_update",
        "hire",
        "manual_edit",
        "manual_edit",
        "manual_edit",
    ]
    assert [row.change_type for row in descending["items"]] == [
        "manual_edit",
        "manual_edit",
        "manual_edit",
        "hire",
        "bulk_update",
        "bulk_update",
    ]


def test_pagination_is_stable_when_sort_values_tie():
    employee = make_employee()
    rows = [
        make_salary_history(
            employee=employee,
            effective_date=date(2026, 1, 1),
            change_type=SalaryHistory.ChangeType.MANUAL_EDIT,
            reason=f"Review {index}",
        )
        for index in range(5)
    ]
    expected_ids = [row.id for row in reversed(rows)]

    collected = []
    for page in range(1, 4):
        result = list_salary_history(page=page, page_size=2)
        assert result["total"] == 5
        collected.extend(row.id for row in result["items"])

    assert collected == expected_ids


def test_search_uses_one_joined_query_and_one_count_query(
    django_assert_num_queries,
):
    employee = make_employee()
    make_salary_history(employee=employee)
    make_salary_history(employee=employee)

    with django_assert_num_queries(2):
        result = list_salary_history(page_size=1)

    assert result["total"] == 2
    assert len(result["items"]) == 1
