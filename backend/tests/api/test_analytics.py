import pytest

from tests.factories import make_analytics_dataset

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "path",
    ["/api/analytics/summary", "/api/analytics/breakdown?group_by=country"],
)
def test_analytics_routes_require_authentication(client, path):
    response = client.get(path)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_summary_returns_the_golden_payload(auth_client):
    make_analytics_dataset()

    response = auth_client.get("/api/analytics/summary")

    assert response.status_code == 200
    assert response.json() == {
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


def test_summary_supports_measure_and_include_inactive(auth_client):
    make_analytics_dataset()

    response = auth_client.get(
        "/api/analytics/summary",
        {"measure": "base", "include_inactive": "true"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["headcount"] == 14
    assert payload["total_cents"] == 106_750_000
    assert payload["avg_cents"] == 7_625_000
    assert payload["min_cents"] == 3_000_000
    assert payload["max_cents"] == 20_000_000


def test_breakdown_returns_grouped_rows(auth_client):
    make_analytics_dataset()

    response = auth_client.get(
        "/api/analytics/breakdown",
        {"group_by": "country", "measure": "total"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["group_by"] == "country"
    assert payload["measure"] == "total"
    assert payload["rows"][0] == {
        "key": "US",
        "name": "United States",
        "headcount": 4,
        "total_cents": 42_550_000,
        "avg_cents": 10_637_500,
        "min_cents": 8_050_000,
        "max_cents": 13_800_000,
    }
    assert [row["key"] for row in payload["rows"]] == ["US", "DE", "IN"]


def test_distribution_returns_bands_and_zero_filled_groups(auth_client):
    make_analytics_dataset()

    response = auth_client.get("/api/analytics/distribution")

    assert response.status_code == 200
    payload = response.json()
    assert payload["measure"] == "total"
    assert [band["index"] for band in payload["bands"]] == list(range(7))
    assert payload["groups"] == [
        {
            "key": "all",
            "name": "All employees",
            "headcount": 12,
            "counts": [0, 1, 5, 3, 3, 0, 0],
        }
    ]


def test_distribution_supports_department_grouping(auth_client):
    make_analytics_dataset()

    response = auth_client.get(
        "/api/analytics/distribution",
        {"group_by": "department"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert [group["name"] for group in payload["groups"]] == [
        "Engineering",
        "Finance",
        "Sales",
    ]
    for group in payload["groups"]:
        assert len(group["counts"]) == 7
        assert sum(group["counts"]) == group["headcount"]


def test_breakdown_applies_scope_filters(auth_client):
    data = make_analytics_dataset()

    response = auth_client.get(
        "/api/analytics/breakdown",
        {
            "group_by": "department",
            "department_id": data["departments"]["finance"].id,
            "sort_by": "name",
            "sort_dir": "asc",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [row["name"] for row in payload["rows"]] == ["Finance"]
    assert payload["rows"][0]["headcount"] == 3
    assert payload["rows"][0]["total_cents"] == 19_250_000


@pytest.mark.parametrize(
    ("path", "params"),
    [
        ("/api/analytics/summary", {"measure": "median"}),
        ("/api/analytics/summary", {"country_code": "USA"}),
        ("/api/analytics/summary", {"department_id": "not-an-id"}),
        ("/api/analytics/summary", {"include_inactive": "sometimes"}),
        ("/api/analytics/breakdown", {}),
        ("/api/analytics/breakdown", {"group_by": "team"}),
        ("/api/analytics/breakdown", {"group_by": "country", "measure": "median"}),
        ("/api/analytics/breakdown", {"group_by": "country", "sort_by": "median"}),
        ("/api/analytics/breakdown", {"group_by": "country", "sort_dir": "sideways"}),
        ("/api/analytics/breakdown", {"group_by": "country", "limit": "0"}),
        ("/api/analytics/breakdown", {"group_by": "country", "limit": "101"}),
        ("/api/analytics/distribution", {"group_by": "job_title"}),
        ("/api/analytics/distribution", {"measure": "median"}),
        ("/api/analytics/distribution", {"include_inactive": "sometimes"}),
    ],
)
def test_invalid_analytics_query_parameters_return_422(auth_client, path, params):
    response = auth_client.get(path, params)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
