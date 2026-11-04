from datetime import date

import pytest

from employees.models import Employee, SalaryHistory
from employees.serializers import MAX_AMOUNT_CENTS
from tests.factories import (
    make_country,
    make_department,
    make_employee,
    make_job_title,
)

pytestmark = pytest.mark.django_db


def preview_payload(**overrides):
    payload = {
        "filter": {},
        "apply_to_all": False,
        "component": "allowances",
        "mode": "fixed_amount",
        "amount_cents": 120_000,
    }
    payload.update(overrides)
    return payload


def apply_payload(expected_count, **overrides):
    payload = preview_payload(**overrides)
    payload["expected_count"] = expected_count
    payload["reason"] = "FY27 team allowance"
    return payload


def make_filtered_employee(**overrides):
    engineering = make_department("Engineering")
    software_engineer = make_job_title("Software Engineer", 2)
    india = make_country("IN", "India", "INR")
    data = {
        "department": engineering,
        "job_title": software_engineer,
        "country": india,
    }
    data.update(overrides)
    return make_employee(**data)


@pytest.mark.parametrize("path", ["/api/bulk-updates/preview", "/api/bulk-updates/apply"])
def test_bulk_routes_require_authentication(client, path):
    response = client.post(path, preview_payload(), format="json")

    assert response.status_code == 401


def test_preview_fixed_amount_returns_sums_and_sample_without_changes(auth_client):
    first = make_filtered_employee(
        full_name="First",
        email="first@acme.example",
        allowances_cents=200_000,
    )
    second = make_filtered_employee(
        full_name="Second",
        email="second@acme.example",
        allowances_cents=200_000,
    )
    make_filtered_employee(
        full_name="Inactive",
        email="inactive@acme.example",
        allowances_cents=200_000,
        status=Employee.Status.INACTIVE,
    )

    response = auth_client.post(
        "/api/bulk-updates/preview",
        preview_payload(
            filter={"department_id": first.department_id},
            component="allowances",
            mode="fixed_amount",
            amount_cents=120_000,
        ),
        format="json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["affected_count"] == 2
    assert payload["sum_before_cents"] == 400_000
    assert payload["sum_after_cents"] == 640_000
    assert payload["sum_delta_cents"] == 240_000
    assert payload["sample"] == [
        {
            "id": first.id,
            "full_name": "First",
            "before_cents": 200_000,
            "after_cents": 320_000,
        },
        {
            "id": second.id,
            "full_name": "Second",
            "before_cents": 200_000,
            "after_cents": 320_000,
        },
    ]
    first.refresh_from_db()
    assert first.allowances_cents == 200_000


def test_preview_percent_rounds_half_away_from_zero(auth_client):
    employee = make_filtered_employee(
        full_name="Round",
        email="round@acme.example",
        base_salary_cents=1_050,
    )

    response = auth_client.post(
        "/api/bulk-updates/preview",
        preview_payload(
            filter={"department_id": employee.department_id},
            component="base",
            mode="percent",
            percentage="5.00",
            amount_cents=None,
        ),
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["sample"] == [
        {
            "id": employee.id,
            "full_name": "Round",
            "before_cents": 1_050,
            "after_cents": 1_103,
        }
    ]


def test_zero_bonus_is_not_affected_by_percent_change(auth_client):
    employee = make_filtered_employee(
        full_name="No bonus",
        email="no.bonus@acme.example",
        bonus_cents=0,
    )

    response = auth_client.post(
        "/api/bulk-updates/preview",
        preview_payload(
            filter={"department_id": employee.department_id},
            component="bonus",
            mode="percent",
            percentage="10.00",
            amount_cents=None,
        ),
        format="json",
    )

    assert response.status_code == 200
    assert response.json()["affected_count"] == 0
    assert response.json()["sample"] == []


def test_apply_fixed_amount_updates_only_component_and_writes_shared_history(
    auth_client,
    fixed_clock,
):
    first = make_filtered_employee(
        full_name="First",
        email="first@acme.example",
        base_salary_cents=5_000_000,
        bonus_cents=500_000,
        allowances_cents=200_000,
    )
    second = make_filtered_employee(
        full_name="Second",
        email="second@acme.example",
        base_salary_cents=4_000_000,
        bonus_cents=400_000,
        allowances_cents=100_000,
    )
    make_filtered_employee(
        full_name="Inactive",
        email="inactive@acme.example",
        allowances_cents=200_000,
        status=Employee.Status.INACTIVE,
    )
    payload = apply_payload(
        2,
        filter={"department_id": first.department_id},
        component="allowances",
        mode="fixed_amount",
        amount_cents=120_000,
    )

    response = auth_client.post("/api/bulk-updates/apply", payload, format="json")

    assert response.status_code == 200
    result = response.json()
    assert result["component"] == "allowances"
    assert result["affected_count"] == 2
    assert result["sum_delta_cents"] == 240_000
    assert result["batch_id"]
    first.refresh_from_db()
    second.refresh_from_db()
    assert first.allowances_cents == 320_000
    assert second.allowances_cents == 220_000
    assert first.base_salary_cents == 5_000_000
    assert first.bonus_cents == 500_000
    histories = SalaryHistory.objects.order_by("employee_id")
    assert histories.count() == 2
    assert {str(row.batch_id) for row in histories} == {result["batch_id"]}
    for row in histories:
        assert row.change_type == SalaryHistory.ChangeType.BULK_UPDATE
        assert row.effective_date == date(2026, 10, 31)
        assert row.reason == "FY27 team allowance"
    assert histories[0].prev_allowances_cents == 200_000
    assert histories[0].allowances_cents == 320_000


def test_apply_stale_preview_changes_nothing(auth_client):
    employee = make_filtered_employee(
        full_name="First",
        email="first@acme.example",
        allowances_cents=200_000,
    )
    make_filtered_employee(
        full_name="Second",
        email="second@acme.example",
        allowances_cents=200_000,
    )

    response = auth_client.post(
        "/api/bulk-updates/apply",
        apply_payload(
            1,
            filter={"department_id": employee.department_id},
            component="allowances",
            mode="fixed_amount",
            amount_cents=120_000,
        ),
        format="json",
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "stale_preview"
    employee.refresh_from_db()
    assert employee.allowances_cents == 200_000
    assert SalaryHistory.objects.count() == 0


def test_apply_result_too_large_changes_nothing(auth_client):
    employee = make_filtered_employee(
        full_name="Large",
        email="large@acme.example",
        base_salary_cents=MAX_AMOUNT_CENTS - 1,
    )

    response = auth_client.post(
        "/api/bulk-updates/apply",
        apply_payload(
            1,
            filter={"department_id": employee.department_id},
            component="base",
            mode="fixed_amount",
            amount_cents=2,
        ),
        format="json",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "result_too_large"
    employee.refresh_from_db()
    assert employee.base_salary_cents == MAX_AMOUNT_CENTS - 1
    assert SalaryHistory.objects.count() == 0


@pytest.mark.parametrize(
    "payload",
    [
        {
            "filter": {},
            "apply_to_all": False,
            "component": "base",
            "mode": "fixed_amount",
            "amount_cents": 100,
        },
        {
            "filter": {"department_id": 1},
            "apply_to_all": False,
            "component": "base",
            "mode": "percent",
            "percentage": "5.00",
            "amount_cents": 100,
        },
        {
            "filter": {"department_id": 1},
            "apply_to_all": False,
            "component": "base",
            "mode": "fixed_amount",
            "percentage": "5.00",
            "amount_cents": 100,
        },
        {
            "filter": {"department_id": 1},
            "apply_to_all": False,
            "component": "base",
            "mode": "percent",
            "percentage": "0.00",
        },
        {
            "filter": {"department_id": 1},
            "apply_to_all": False,
            "component": "base",
            "mode": "percent",
            "percentage": "101.00",
        },
        {
            "filter": {"department_id": 1},
            "apply_to_all": False,
            "component": "base",
            "mode": "fixed_amount",
            "amount_cents": 0,
        },
    ],
)
def test_preview_rejects_invalid_mode_combinations(auth_client, payload):
    response = auth_client.post(
        "/api/bulk-updates/preview",
        payload,
        format="json",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_apply_to_all_without_filter_updates_all_active_employees(auth_client):
    first = make_filtered_employee(
        full_name="First",
        email="first@acme.example",
        bonus_cents=100_000,
    )
    second = make_filtered_employee(
        full_name="Second",
        email="second@acme.example",
        bonus_cents=100_000,
    )
    inactive = make_filtered_employee(
        full_name="Inactive",
        email="inactive@acme.example",
        bonus_cents=100_000,
        status=Employee.Status.INACTIVE,
    )

    response = auth_client.post(
        "/api/bulk-updates/apply",
        apply_payload(
            2,
            filter={},
            apply_to_all=True,
            component="bonus",
            mode="fixed_amount",
            amount_cents=50_000,
        ),
        format="json",
    )

    assert response.status_code == 200
    first.refresh_from_db()
    second.refresh_from_db()
    inactive.refresh_from_db()
    assert first.bonus_cents == 150_000
    assert second.bonus_cents == 150_000
    assert inactive.bonus_cents == 100_000
    assert SalaryHistory.objects.count() == 2


@pytest.mark.parametrize(
    "overrides",
    [
        {"expected_count": None},
        {"reason": ""},
        {"reason": "x" * 201},
    ],
)
def test_apply_rejects_missing_or_invalid_expected_count_and_reason(auth_client, overrides):
    employee = make_filtered_employee(
        full_name="First",
        email="first@acme.example",
    )
    payload = apply_payload(
        1,
        filter={"department_id": employee.department_id},
        component="allowances",
        mode="fixed_amount",
        amount_cents=10_000,
    )
    payload.update(overrides)
    if payload.get("expected_count") is None:
        payload.pop("expected_count", None)

    response = auth_client.post("/api/bulk-updates/apply", payload, format="json")

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
