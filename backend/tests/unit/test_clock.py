from datetime import UTC, date, datetime


def test_fixed_clock_can_be_installed_and_restored(fixed_clock):
    assert fixed_clock.today() == date(2026, 10, 31)
    assert fixed_clock.now() == datetime(2026, 10, 31, 12, 0, tzinfo=UTC)
