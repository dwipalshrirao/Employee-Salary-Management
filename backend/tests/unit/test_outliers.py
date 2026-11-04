from decimal import Decimal

import pytest

from analytics.services import get_outliers
from tests.factories import make_outlier_dataset

pytestmark = pytest.mark.django_db


def test_outliers_use_two_queries(django_assert_num_queries):
    make_outlier_dataset()

    with django_assert_num_queries(2):
        get_outliers()


def test_outliers_include_high_earners_sorted_by_ratio():
    data = make_outlier_dataset()

    result = get_outliers()

    assert result["total"] == 2
    assert result["page"] == 1
    assert result["page_size"] == 25
    assert result["items"] == [
        {
            "employee_id": data["employees"]["in_outlier"].id,
            "full_name": "IN Outlier",
            "job_title": "Account Executive",
            "country": "India",
            "amount_cents": 15_000_000,
            "peer_avg_cents": 7_000_000,
            "ratio": 2.14,
        },
        {
            "employee_id": data["employees"]["us_outlier"].id,
            "full_name": "US Outlier",
            "job_title": "Software Engineer",
            "country": "United States",
            "amount_cents": 25_000_000,
            "peer_avg_cents": 13_000_000,
            "ratio": 1.92,
        },
    ]


def test_outliers_respect_threshold_and_min_peers():
    make_outlier_dataset()

    threshold = get_outliers(threshold=Decimal("2.0"))
    min_peers = get_outliers(min_peers=6)
    smaller_peer_group = get_outliers(min_peers=4)

    assert [item["full_name"] for item in threshold["items"]] == ["IN Outlier"]
    assert min_peers["items"] == []
    assert [item["full_name"] for item in smaller_peer_group["items"]] == [
        "IN Outlier",
        "DE High",
        "US Outlier",
    ]


def test_outliers_ignore_inactive_employees_and_peer_averages():
    make_outlier_dataset()

    result = get_outliers()

    names = [item["full_name"] for item in result["items"]]
    assert "US Inactive" not in names
    assert result["items"][1]["peer_avg_cents"] == 13_000_000


def test_outliers_support_measure_and_scope_filters():
    make_outlier_dataset()

    base = get_outliers(measure="base")
    india = get_outliers(country_code="IN")

    assert [item["full_name"] for item in base["items"]] == ["US Outlier"]
    assert [item["full_name"] for item in india["items"]] == ["IN Outlier"]


def test_outliers_paginate_and_keep_ratio_order():
    make_outlier_dataset()

    first = get_outliers(page=1, page_size=1)
    second = get_outliers(page=2, page_size=1)

    assert first["total"] == 2
    assert first["items"][0]["full_name"] == "IN Outlier"
    assert second["items"][0]["full_name"] == "US Outlier"
