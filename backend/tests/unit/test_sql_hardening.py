from decimal import Decimal

import pytest

import analytics.services as services
from analytics.services import get_outliers
from tests.factories import make_employee

pytestmark = pytest.mark.django_db


class RecordingCursor:
    def __init__(self):
        self.calls = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params=()):
        self.calls.append((sql, tuple(params)))

    def fetchone(self):
        return (0,)

    def fetchall(self):
        return []


def test_outlier_scope_values_are_bound_not_interpolated(monkeypatch):
    cursor = RecordingCursor()
    monkeypatch.setattr(services.connection, "cursor", lambda: cursor)
    attack = "' OR 1=1 --"

    get_outliers(
        country_code=attack,
        department_id=1,
        job_title_id=1,
        threshold=Decimal("1.5"),
    )

    assert len(cursor.calls) == 2
    for sql, _params in cursor.calls:
        assert attack not in sql
        assert "DROP TABLE" not in sql.upper()

    assert attack in cursor.calls[0][1]
    assert attack in cursor.calls[1][1]


def test_outlier_measure_is_whitelisted():
    with pytest.raises(ValueError):
        get_outliers(measure="total_comp_cents; DROP TABLE employees")


def test_injection_text_is_treated_as_literal_search(auth_client):
    make_employee(full_name="Asha Patel")

    response = auth_client.get("/api/employees", {"q": "' OR 1=1 --"})

    assert response.status_code == 200
    assert response.json()["items"] == []
