import datetime

from ffun.core import utils
from ffun.domain.entities import Days
from ffun.feeds import utils as f_utils
from ffun.feeds.entities import Feed


class TestEntriesPerDay:

    def test_uses_feed_age_when_feed_is_younger_than_period(self, loaded_feed: Feed) -> None:
        now = utils.now()
        feed = loaded_feed.replace(created_at=now - datetime.timedelta(days=2))

        assert f_utils.entries_per_day(feed, entries_loaded=5, period=Days(30), now=now) == 3

    def test_uses_period_when_feed_is_older_than_period(self, loaded_feed: Feed) -> None:
        now = utils.now()
        feed = loaded_feed.replace(created_at=now - datetime.timedelta(days=100))

        assert f_utils.entries_per_day(feed, entries_loaded=31, period=Days(30), now=now) == 2

    def test_uses_one_day_for_new_feed(self, loaded_feed: Feed) -> None:
        now = utils.now()
        feed = loaded_feed.replace(created_at=now)

        assert f_utils.entries_per_day(feed, entries_loaded=3, period=Days(30), now=now) == 3

    def test_returns_zero_when_no_entries_loaded(self, loaded_feed: Feed) -> None:
        now = utils.now()
        feed = loaded_feed.replace(created_at=now)

        assert f_utils.entries_per_day(feed, entries_loaded=0, period=Days(30), now=now) == 0


class TestIsYoung:

    def test_returns_true_when_feed_is_younger_than_period(self, loaded_feed: Feed) -> None:
        now = utils.now()
        feed = loaded_feed.replace(created_at=now - datetime.timedelta(days=29))

        assert f_utils.is_young(feed, period=Days(30), now=now)

    def test_returns_false_when_feed_age_equals_period(self, loaded_feed: Feed) -> None:
        now = utils.now()
        feed = loaded_feed.replace(created_at=now - datetime.timedelta(days=30))

        assert not f_utils.is_young(feed, period=Days(30), now=now)

    def test_returns_false_when_feed_is_older_than_period(self, loaded_feed: Feed) -> None:
        now = utils.now()
        feed = loaded_feed.replace(created_at=now - datetime.timedelta(days=31))

        assert not f_utils.is_young(feed, period=Days(30), now=now)
