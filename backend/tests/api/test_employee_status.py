import pytest

from employees.models import Employee, SalaryHistory
from tests.factories import make_employee

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize("action", ["deactivate", "reactivate"])
def test_status_routes_require_authentication(client, action):
    employee = make_employee()

    response = client.post(f"/api/employees/{employee.id}/{action}")

    assert response.status_code == 401


def test_deactivate_sets_inactive(auth_client):
    employee = make_employee()

    response = auth_client.post(f"/api/employees/{employee.id}/deactivate")

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"
    employee.refresh_from_db()
    assert employee.status == Employee.Status.INACTIVE
    assert SalaryHistory.objects.count() == 0


def test_deactivate_is_blocked_by_active_direct_reports(auth_client):
    manager = make_employee(full_name="Manager", email="manager@acme.example")
    make_employee(manager=manager)
    make_employee(manager=manager)

    response = auth_client.post(f"/api/employees/{manager.id}/deactivate")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    assert "2 active direct reports" in response.json()["error"]["message"]
    manager.refresh_from_db()
    assert manager.status == Employee.Status.ACTIVE


def test_deactivate_allows_inactive_direct_reports(auth_client):
    manager = make_employee(full_name="Manager", email="manager@acme.example")
    make_employee(
        manager=manager,
        status=Employee.Status.INACTIVE,
    )

    response = auth_client.post(f"/api/employees/{manager.id}/deactivate")

    assert response.status_code == 200
    manager.refresh_from_db()
    assert manager.status == Employee.Status.INACTIVE


def test_reactivate_sets_active_when_manager_is_active(auth_client):
    manager = make_employee(full_name="Manager", email="manager@acme.example")
    employee = make_employee(
        manager=manager,
        status=Employee.Status.INACTIVE,
    )

    response = auth_client.post(f"/api/employees/{employee.id}/reactivate")

    assert response.status_code == 200
    assert response.json()["status"] == "active"
    employee.refresh_from_db()
    assert employee.status == Employee.Status.ACTIVE


def test_reactivate_without_manager_is_allowed(auth_client):
    employee = make_employee(status=Employee.Status.INACTIVE)

    response = auth_client.post(f"/api/employees/{employee.id}/reactivate")

    assert response.status_code == 200
    employee.refresh_from_db()
    assert employee.status == Employee.Status.ACTIVE


def test_reactivate_is_blocked_when_manager_is_inactive(auth_client):
    manager = make_employee(
        full_name="Inactive Manager",
        email="inactive.manager@acme.example",
        status=Employee.Status.INACTIVE,
    )
    employee = make_employee(
        manager=manager,
        status=Employee.Status.INACTIVE,
    )

    response = auth_client.post(f"/api/employees/{employee.id}/reactivate")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"
    employee.refresh_from_db()
    assert employee.status == Employee.Status.INACTIVE


@pytest.mark.parametrize("action", ["deactivate", "reactivate"])
def test_status_routes_return_404_for_unknown_employee(auth_client, action):
    response = auth_client.post(f"/api/employees/999999/{action}")

    assert response.status_code == 404
