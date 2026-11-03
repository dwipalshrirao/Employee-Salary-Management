from datetime import date

import pytest

from employees.models import Employee
from employees.selectors import list_employees
from tests.factories import (
    make_country,
    make_department,
    make_employee,
    make_job_title,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def list_data():
    engineering = make_department("Engineering")
    sales = make_department("Sales")
    engineer = make_job_title("Software Engineer", 2)
    account_executive = make_job_title("Account Executive", 2)
    india = make_country("IN", "India", "INR")
    united_states = make_country("US", "United States", "USD")
    manager = make_employee(
        full_name="Ravi Shah",
        email="ravi@acme.example",
        department=engineering,
        job_title=engineer,
        country=india,
    )
    asha = make_employee(
        full_name="Asha Patel",
        email="asha@acme.example",
        department=engineering,
        job_title=engineer,
        country=india,
        manager=manager,
    )
    john = make_employee(
        full_name="John Smith",
        email="john@acme.example",
        department=sales,
        job_title=account_executive,
        country=united_states,
        status=Employee.Status.INACTIVE,
    )
    percent = make_employee(
        full_name="100% Match",
        email="percent@acme.example",
        department=sales,
        job_title=account_executive,
        country=united_states,
    )
    underscore = make_employee(
        full_name="Under_score",
        email="underscore@acme.example",
        department=sales,
        job_title=account_executive,
        country=united_states,
    )
    return {
        "engineering": engineering,
        "sales": sales,
        "engineer": engineer,
        "account_executive": account_executive,
        "india": india,
        "united_states": united_states,
        "manager": manager,
        "asha": asha,
        "john": john,
        "percent": percent,
        "underscore": underscore,
    }


def test_list_defaults_to_active_employees(list_data):
    result = list_employees()

    returned_ids = {employee.id for employee in result["items"]}
    assert result["total"] == 4
    assert list_data["john"].id not in returned_ids
    assert returned_ids == {
        list_data["manager"].id,
        list_data["asha"].id,
        list_data["percent"].id,
        list_data["underscore"].id,
    }


def test_search_matches_name_and_email_and_treats_wildcards_literally(list_data):
    name_result = list_employees(q="asha")
    email_result = list_employees(q="RAVI@ACME")
    percent_result = list_employees(q="%")
    underscore_result = list_employees(q="_")

    assert [employee.id for employee in name_result["items"]] == [list_data["asha"].id]
    assert [employee.id for employee in email_result["items"]] == [
        list_data["manager"].id
    ]
    assert [employee.id for employee in percent_result["items"]] == [
        list_data["percent"].id
    ]
    assert [employee.id for employee in underscore_result["items"]] == [
        list_data["underscore"].id
    ]


def test_filters_can_be_combined(list_data):
    result = list_employees(
        country_code="US",
        department_id=list_data["sales"].id,
        job_title_id=list_data["account_executive"].id,
        status="all",
    )

    assert {employee.id for employee in result["items"]} == {
        list_data["john"].id,
        list_data["percent"].id,
        list_data["underscore"].id,
    }
    assert result["total"] == 3


def test_manager_filter_returns_direct_reports(list_data):
    result = list_employees(manager_id=list_data["manager"].id)

    assert [employee.id for employee in result["items"]] == [list_data["asha"].id]


def test_status_inactive_and_all(list_data):
    inactive = list_employees(status="inactive")
    all_employees = list_employees(status="all")

    assert [employee.id for employee in inactive["items"]] == [list_data["john"].id]
    assert all_employees["total"] == 5


@pytest.fixture
def sort_data():
    engineering = make_department("Engineering")
    sales = make_department("Sales")
    marketing = make_department("Marketing")
    zeta = make_job_title("Zeta Role", 2)
    alpha = make_job_title("Alpha Role", 2)
    middle = make_job_title("Middle Role", 2)
    united_states = make_country("US", "United States", "USD")
    india = make_country("IN", "India", "INR")
    canada = make_country("CA", "Canada", "CAD")

    first = make_employee(
        full_name="Alpha",
        email="zulu@acme.example",
        department=engineering,
        job_title=zeta,
        country=united_states,
        hire_date=date(2020, 1, 1),
        base_salary_cents=1_000,
        bonus_cents=0,
        allowances_cents=0,
    )
    second = make_employee(
        full_name="Zulu",
        email="alpha@acme.example",
        department=sales,
        job_title=alpha,
        country=india,
        hire_date=date(2022, 1, 1),
        base_salary_cents=3_000,
        bonus_cents=0,
        allowances_cents=0,
    )
    third = make_employee(
        full_name="Mike",
        email="mike@acme.example",
        department=marketing,
        job_title=middle,
        country=canada,
        hire_date=date(2021, 1, 1),
        base_salary_cents=2_000,
        bonus_cents=0,
        allowances_cents=0,
    )
    return {"first": first, "second": second, "third": third}


@pytest.mark.parametrize(
    ("sort_by", "ascending_ids"),
    [
        ("full_name", ["first", "third", "second"]),
        ("email", ["second", "third", "first"]),
        ("hire_date", ["first", "third", "second"]),
        ("base_salary", ["first", "third", "second"]),
        ("total_comp", ["first", "third", "second"]),
        ("department", ["first", "third", "second"]),
        ("job_title", ["second", "third", "first"]),
        ("country", ["third", "second", "first"]),
    ],
)
def test_sort_fields_and_directions(sort_data, sort_by, ascending_ids):
    ascending = list_employees(sort_by=sort_by, sort_dir="asc")
    descending = list_employees(sort_by=sort_by, sort_dir="desc")
    expected_ascending = [sort_data[key].id for key in ascending_ids]
    expected_descending = list(reversed(expected_ascending))

    assert [employee.id for employee in ascending["items"]] == expected_ascending
    assert [employee.id for employee in descending["items"]] == expected_descending


def test_pagination_is_stable_when_sort_values_tie():
    employees = [
        make_employee(full_name="Same Name", email=f"same{index}@acme.example")
        for index in range(5)
    ]
    expected_ids = [employee.id for employee in employees]

    collected = []
    for page in range(1, 4):
        result = list_employees(
            sort_by="full_name",
            page=page,
            page_size=2,
        )
        assert result["total"] == 5
        collected.extend(employee.id for employee in result["items"])

    assert collected == expected_ids


def test_list_uses_one_joined_query_and_one_count_query(django_assert_num_queries):
    make_employee(full_name="First")
    make_employee(full_name="Second")

    with django_assert_num_queries(2):
        result = list_employees(page_size=1)

    assert result["total"] == 2
    assert len(result["items"]) == 1
