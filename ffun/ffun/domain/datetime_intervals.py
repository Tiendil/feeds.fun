import datetime

from ffun.core import utils

LIFETIME_INTERVAL_START_MARKER = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)
LIFETIME_INTERVAL_END_MARKER = datetime.datetime.max.replace(tzinfo=datetime.UTC)


def day_interval_start(now: datetime.datetime | None = None) -> datetime.datetime:
    if now is None:
        now = utils.now()

    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def month_interval_start(now: datetime.datetime | None = None) -> datetime.datetime:
    if now is None:
        now = utils.now()

    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def next_month_start(now: datetime.datetime | None = None) -> datetime.datetime:
    current_month_started_at = month_interval_start(now)

    if current_month_started_at.month == 12:
        return current_month_started_at.replace(year=current_month_started_at.year + 1, month=1)

    return current_month_started_at.replace(month=current_month_started_at.month + 1)
