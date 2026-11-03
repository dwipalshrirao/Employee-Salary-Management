"""Display-only conversion of USD cents into the country currency."""

from decimal import ROUND_HALF_UP, Decimal


def convert_usd_cents(cents, rate_per_usd):
    """Convert USD cents using round-half-up, never binary float rounding."""
    amount = Decimal(cents) * Decimal(str(rate_per_usd))
    return int(amount.to_integral_value(rounding=ROUND_HALF_UP))


def local_amounts(employee):
    """Build the local-currency block for an employee detail response."""
    rate = employee.country.currency_code.rate_per_usd
    return {
        "currency_code": employee.country.currency_code_id,
        "rate_per_usd": rate,
        "base_salary_cents": convert_usd_cents(employee.base_salary_cents, rate),
        "bonus_cents": convert_usd_cents(employee.bonus_cents, rate),
        "allowances_cents": convert_usd_cents(employee.allowances_cents, rate),
        "total_comp_cents": convert_usd_cents(employee.total_comp_cents, rate),
    }
