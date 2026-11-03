from datetime import UTC, date, datetime


class Clock:
    def today(self) -> date:
        return datetime.now(UTC).date()

    def now(self) -> datetime:
        return datetime.now(UTC)


CLOCK = Clock()


def get_clock() -> Clock:
    return CLOCK
