from employees.local_currency import convert_usd_cents


def test_local_amount_rounds_half_up():
    assert convert_usd_cents(3, 0.5) == 2
    assert convert_usd_cents(1, 1.5) == 2


def test_local_amount_uses_integer_cents_and_decimal_rate():
    assert convert_usd_cents(4_500_000, 83.0) == 373_500_000
    assert convert_usd_cents(123, 1.36) == 167
