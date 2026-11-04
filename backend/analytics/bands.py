"""Salary distribution bands, defined once for API metadata and SQL."""

from django.db.models import Case, IntegerField, Value, When

BANDS = (
    {"index": 0, "label": "< $30k", "upper_bound": 3_000_000},
    {"index": 1, "label": "$30k - $50k", "upper_bound": 5_000_000},
    {"index": 2, "label": "$50k - $75k", "upper_bound": 7_500_000},
    {"index": 3, "label": "$75k - $100k", "upper_bound": 10_000_000},
    {"index": 4, "label": "$100k - $150k", "upper_bound": 15_000_000},
    {"index": 5, "label": "$150k - $200k", "upper_bound": 20_000_000},
    {"index": 6, "label": "$200k+", "upper_bound": None},
)


def band_metadata():
    return [{"index": band["index"], "label": band["label"]} for band in BANDS]


def band_case(field):
    """Map a whitelisted measure column to its band index in SQL."""
    whens = [
        When(**{f"{field}__lt": band["upper_bound"]}, then=Value(band["index"]))
        for band in BANDS
        if band["upper_bound"] is not None
    ]
    return Case(*whens, default=Value(BANDS[-1]["index"]), output_field=IntegerField())
