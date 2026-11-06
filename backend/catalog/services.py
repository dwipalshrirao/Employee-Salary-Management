"""Currency rate services."""

import math
import re

from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import ValidationError

from catalog.models import Country, CurrencyRate
from common.clock import get_clock
from common.errors import ConflictError

CURRENCY_CODE_PATTERN = re.compile(r"^[A-Z]{3}$")
MAX_RATE_PER_USD = 1_000_000


def _validate_code(code):
    if not CURRENCY_CODE_PATTERN.fullmatch(code):
        raise ValidationError(
            {"currency_code": ["Currency code must be three uppercase letters."]}
        )


def _validate_rate(rate):
    if not math.isfinite(rate) or rate <= 0 or rate > MAX_RATE_PER_USD:
        raise ValidationError(
            {
                "rate_per_usd": [
                    "Rate must be a finite number greater than 0 and at most 1,000,000."
                ]
            }
        )


def _country_codes(code):
    return list(
        Country.objects.filter(currency_code_id=code)
        .order_by("code")
        .values_list("code", flat=True)
    )


def _with_country_codes(rate):
    rate.country_codes = _country_codes(rate.currency_code)
    return rate


def list_currency_rates():
    """Return all rates sorted by code with their country codes."""
    rates = list(CurrencyRate.objects.order_by("currency_code"))
    codes_by_currency = {}
    for currency_code, country_code in Country.objects.order_by("code").values_list(
        "currency_code_id",
        "code",
    ):
        codes_by_currency.setdefault(currency_code, []).append(country_code)

    for rate in rates:
        rate.country_codes = codes_by_currency.get(rate.currency_code, [])
    return rates


def get_currency_rate(code):
    """Return one rate with its country codes, or raise 404."""
    return _with_country_codes(get_object_or_404(CurrencyRate, pk=code))


def create_currency_rate(data, clock=None):
    """Create a currency rate with a timestamp from the injected clock."""
    clock = clock or get_clock()
    code = data.get("currency_code", "")
    rate = data.get("rate_per_usd")
    _validate_code(code)
    _validate_rate(rate)

    if CurrencyRate.objects.filter(pk=code).exists():
        raise ConflictError(
            "Currency already exists.",
            details={"currency_code": code},
        )

    try:
        with transaction.atomic():
            created = CurrencyRate.objects.create(
                currency_code=code,
                rate_per_usd=rate,
                updated_at=clock.now(),
            )
    except IntegrityError as exc:
        raise ConflictError(
            "Currency already exists.",
            details={"currency_code": code},
        ) from exc

    return _with_country_codes(created)


def update_currency_rate(code, data, clock=None):
    """Change a rate unless it is USD, the fixed base currency."""
    clock = clock or get_clock()
    rate = get_object_or_404(CurrencyRate, pk=code)
    if code == "USD":
        raise ValidationError(
            {"rate_per_usd": ["USD is the base currency and its rate cannot be changed."]}
        )

    new_rate = data.get("rate_per_usd")
    _validate_rate(new_rate)
    with transaction.atomic():
        rate.rate_per_usd = new_rate
        rate.updated_at = clock.now()
        rate.save(update_fields=["rate_per_usd", "updated_at"])

    return _with_country_codes(rate)


def delete_currency_rate(code):
    """Delete an unused non-USD currency rate."""
    rate = get_object_or_404(CurrencyRate, pk=code)
    if code == "USD":
        raise ConflictError("USD is the base currency and cannot be deleted.")

    country_codes = _country_codes(code)
    if country_codes:
        joined = ", ".join(country_codes)
        raise ConflictError(
            f"Currency is used by countries: {joined}.",
            details={"country_codes": country_codes},
        )

    with transaction.atomic():
        rate.delete()
