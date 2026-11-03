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


@pytest.fixture
def create_refs():
    return {
        "department": make_department("Engineering"),
        "job_title": make_job_title("Software Engineer", 2),
        "country": make_country("US", "United States", "USD"),
    }


def create_payload(refs, **overrides):
    payload = {
        "full_name": "New Employee",
        "email": "new.employee@acme.example",
        "department_id": refs["department"].id,
        "job_title_id": refs["job_title"].id,
        "country_code": refs["country"].code,
        "hire_date": "2026-10-01",
        "base_salary_cents": 4_500_000,
        "bonus_cents": 450_000,
        "allowances_cents": 180_000,
    }
    payload.update(overrides)
    return payload


def test_create_employee_requires_authentication(client, create_refs):
    response = client.post(
        "/api/employees",
        create_payload(create_refs),
        format="json",
    )

    assert response.status_code == 401


def test_create_employee_writes_employee_and_hire_history(
    auth_client,
    create_refs,
    fixed_clock,
):
    response = auth_client.post(
        "/api/employees",
        create_payload(create_refs),
        format="json",
    )

    assert response.status_code == 201
    employee = Employee.objects.get(email="new.employee@acme.example")
    assert response.json()["id"] == employee.id
    assert response.json()["direct_reports_count"] == 0
    assert employee.status == Employee.Status.ACTIVE
    assert employee.base_salary_cents == 4_500_000
    assert employee.total_comp_cents == 5_130_000
    history = SalaryHistory.objects.get(employee=employee)
    assert history.change_type == SalaryHistory.ChangeType.HIRE
    assert history.effective_date.isoformat() == "2026-10-01"
    assert history.reason == "New hire"
    assert history.base_salary_cents == 4_500_000
    assert history.bonus_cents == 450_000
    assert history.allowances_cents == 180_000
    assert history.prev_base_salary_cents is None
    assert history.prev_bonus_cents is None
    assert history.prev_allowances_cents is None


def test_create_employee_with_active_manager(auth_client, create_refs):
    manager = make_employee(full_name="Ravi Shah", email="ravi@acme.example")

    response = auth_client.post(
        "/api/employees",
        create_payload(create_refs, manager_id=manager.id),
        format="json",
    )

    assert response.status_code == 201
    employee = Employee.objects.get(email="new.employee@acme.example")
    assert employee.manager_id == manager.id


def test_create_employee_rejects_inactive_manager(auth_client, create_refs):
    manager = make_employee(
        full_name="Inactive Manager",
        email="inactive.manager@acme.example",
        status=Employee.Status.INACTIVE,
    )

    response = auth_client.post(
        "/api/employees",
        create_payload(create_refs, manager_id=manager.id),
        format="json",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert Employee.objects.count() == 1


def test_create_employee_rejects_unknown_manager(auth_client, create_refs):
    response = auth_client.post(
        "/api/employees",
        create_payload(create_refs, manager_id=999999),
        format="json",
    )

    assert response.status_code == 422
    assert Employee.objects.count() == 0


def test_create_employee_rejects_future_hire_date(auth_client, create_refs, fixed_clock):
    response = auth_client.post(
        "/api/employees",
        create_payload(create_refs, hire_date="2026-11-01"),
        format="json",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert Employee.objects.count() == 0


def test_create_employee_rejects_unknown_lookups(auth_client, create_refs):
    response = auth_client.post(
        "/api/employees",
        create_payload(create_refs, department_id=999999),
        format="json",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert Employee.objects.count() == 0


@pytest.mark.parametrize(
    "field",
    ["status", "id", "total_comp_cents", "password"],
)
def test_create_employee_rejects_extra_fields(auth_client, create_refs, field):
    response = auth_client.post(
        "/api/employees",
        create_payload(create_refs, **{field: "not-allowed"}),
        format="json",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert Employee.objects.count() == 0


def test_create_employee_rejects_case_insensitive_duplicate_email(auth_client, create_refs):
    make_employee(full_name="Existing", email="existing@acme.example")

    response = auth_client.post(
        "/api/employees",
        create_payload(create_refs, email="EXISTING@ACME.EXAMPLE"),
        format="json",
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert response.json()["error"]["details"]["field"] == "email"
    assert Employee.objects.filter(email__iexact="existing@acme.example").count() == 1
    assert SalaryHistory.objects.count() == 0


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("full_name", ""),
        ("full_name", "x" * 121),
        ("email", "not-an-email"),
        ("base_salary_cents", 0),
        ("base_salary_cents", MAX_AMOUNT_CENTS + 1),
        ("bonus_cents", -1),
        ("bonus_cents", MAX_AMOUNT_CENTS + 1),
        ("allowances_cents", -1),
        ("allowances_cents", MAX_AMOUNT_CENTS + 1),
    ],
)
def test_create_employee_validates_fields(auth_client, create_refs, field, value):
    response = auth_client.post(
        "/api/employees",
        create_payload(create_refs, **{field: value}),
        format="json",
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    assert Employee.objects.count() == 0
