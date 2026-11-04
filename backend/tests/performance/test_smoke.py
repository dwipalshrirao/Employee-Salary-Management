import statistics
import time

import pytest
from django.core.management import call_command
from rest_framework.test import APIClient

from accounts.models import HrUser
from employees.models import Employee

pytestmark = [pytest.mark.slow, pytest.mark.django_db]


@pytest.fixture(scope="module")
def seeded_10k(django_db_setup, django_db_blocker):
    with django_db_blocker.unblock():
        started = time.perf_counter()
        call_command("seed", employees=10_000, seed=42, reset=True, verbosity=0)
        elapsed = time.perf_counter() - started

    yield elapsed

    with django_db_blocker.unblock():
        call_command("flush", interactive=False, verbosity=0)


@pytest.fixture(scope="module")
def perf_client(seeded_10k, django_db_blocker):
    with django_db_blocker.unblock():
        user = HrUser.objects.get(email="hr@acme.example")
        user.set_password("perf-password")
        user.save()

        client = APIClient()
        response = client.post(
            "/api/auth/login",
            {"email": user.email, "password": "perf-password"},
            format="json",
        )
        assert response.status_code == 200
        return client


def _median_ms(call, repeats=3):
    call()
    samples = []
    for _ in range(repeats):
        started = time.perf_counter()
        call()
        samples.append((time.perf_counter() - started) * 1000)
    return statistics.median(samples)


def test_seed_target(seeded_10k):
    assert seeded_10k < 45


def test_employee_list_under_3x_target(perf_client, seeded_10k):
    elapsed = _median_ms(
        lambda: perf_client.get(
            "/api/employees",
            {
                "status": "active",
                "country_code": "US",
                "sort_by": "base_salary",
                "sort_dir": "desc",
                "page": 1,
                "page_size": 25,
            },
        )
    )

    assert elapsed < 450


def test_employee_detail_under_3x_target(perf_client, seeded_10k):
    employee_id = Employee.objects.values_list("id", flat=True).first()

    elapsed = _median_ms(lambda: perf_client.get(f"/api/employees/{employee_id}"))

    assert elapsed < 450


@pytest.mark.parametrize(
    "path",
    [
        "/api/analytics/summary",
        "/api/analytics/breakdown?group_by=country",
        "/api/analytics/distribution",
        "/api/analytics/outliers",
    ],
)
def test_analytics_under_3x_target(perf_client, seeded_10k, path):
    elapsed = _median_ms(lambda: perf_client.get(path))

    assert elapsed < 300


def test_team_analytics_under_3x_target(perf_client, seeded_10k):
    manager_id = (
        Employee.objects.filter(direct_reports__isnull=False)
        .values_list("id", flat=True)
        .first()
    )

    elapsed = _median_ms(
        lambda: perf_client.get(f"/api/analytics/team/{manager_id}")
    )

    assert elapsed < 300
