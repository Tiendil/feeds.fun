import datetime
import math

from ffun.core import utils as core_utils
from ffun.domain.entities import Days
from ffun.feeds.entities import Feed


def entries_per_day(feed: Feed, entries_loaded: int, period: Days, now: datetime.datetime | None = None) -> int:
    assert feed.created_at is not None

    if now is None:
        now = core_utils.now()

    feed_age = max(datetime.timedelta(), now - feed.created_at)
    feed_age_days = math.ceil(feed_age / datetime.timedelta(days=1))
    days = max(1, min(int(period), feed_age_days))

    return math.ceil(entries_loaded / days)


def is_young(feed: Feed, period: Days, now: datetime.datetime | None = None) -> bool:
    assert feed.created_at is not None

    if now is None:
        now = core_utils.now()

    feed_age = max(datetime.timedelta(), now - feed.created_at)

    return feed_age < datetime.timedelta(days=int(period))
