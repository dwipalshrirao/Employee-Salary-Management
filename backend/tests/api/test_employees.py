import pytest

from employees.models import Employee
from tests.factories import make_employee

pytestmark = pytest.mark.django_db


def test_employee_list_requires_authentication(client):
    response = client.get("/api/employees")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_employee_list_returns_default_active_items_with_nested_fields(auth_client):
    manager = make_employee(full_name="Ravi Shah", email="ravi@acme.example")
    report = make_employee(
        full_name="Asha Patel",
        email="asha@acme.example",
        manager=manager,
    )
    make_employee(
        full_name="Inactive Person",
        email="inactive@acme.example",
        status=Employee.Status.INACTIVE,
    )

    response = auth_client.get("/api/employees")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["page"] == 1
    assert payload["page_size"] == 25
    assert len(payload["items"]) == 2

    items = {item["id"]: item for item in payload["items"]}
    assert set(items) == {manager.id, report.id}
    assert items[report.id] == {
        "id": report.id,
        "full_name": "Asha Patel",
        "email": "asha@acme.example",
        "department": {"id": report.department_id, "name": "Engineering"},
        "job_title": {"id": report.job_title_id, "name": "Software Engineer"},
        "country": {"code": "US", "name": "United States"},
        "manager": {"id": manager.id, "full_name": "Ravi Shah"},
        "hire_date": "2021-01-01",
        "status": "active",
        "base_salary_cents": 5_000_000,
        "bonus_cents": 500_000,
        "allowances_cents": 200_000,
        "total_comp_cents": 5_700_000,
    }
    assert items[manager.id]["manager"] is None


def test_employee_list_forwards_search_and_status_filters(auth_client):
    asha = make_employee(
        full_name="Asha Patel",
        email="asha@acme.example",
    )
    make_employee(
        full_name="John Smith",
        email="john@acme.example",
        status=Employee.Status.INACTIVE,
    )

    response = auth_client.get("/api/employees", {"q": "asha", "status": "all"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["id"] for item in payload["items"]] == [asha.id]


@pytest.mark.parametrize(
    "params",
    [
        {"sort_by": "id;drop table employees"},
        {"sort_dir": "sideways"},
        {"page": "0"},
        {"page_size": "101"},
        {"q": "x" * 101},
    ],
)
def test_invalid_list_query_parameters_return_422(auth_client, params):
    response = auth_client.get("/api/employees", params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_employee_list_returns_empty_page(auth_client):
    response = auth_client.get("/api/employees")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "total": 0,
        "page": 1,
        "page_size": 25,
    }


def test_employee_list_returns_requested_page(auth_client):
    for index in range(3):
        make_employee(
            full_name=f"Employee {index}",
            email=f"employee{index}@acme.example",
        )

    response = auth_client.get("/api/employees", {"page": 2, "page_size": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 3
    assert payload["page"] == 2
    assert payload["page_size"] == 1
    assert len(payload["items"]) == 1
