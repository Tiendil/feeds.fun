import pytest

from ffun.core.tests.helpers import assert_compare_xml
from ffun.domain.entities import UnknownUrl
from ffun.domain.urls import normalize_classic_unknown_url, to_feed_url
from ffun.parsers.entities import FeedInfo
from ffun.parsers.opml import create_opml, extract_feeds
from ffun.parsers.tests.helpers import feeds_fixtures_directory, feeds_fixtures_names
from ffun.feeds.entities import Feed
from ffun.domain.urls import url_to_uid


class TestCreateOpml:

    def test(self, saved_feed: Feed, another_saved_feed: Feed) -> None:

        feeds = [saved_feed, another_saved_feed]
        feeds.sort(key=lambda feed: feed.title)

        content = create_opml(feeds)

        expected_content = f'<opml version="2.0"><head><title>Your subscriptions in feeds.fun</title></head><body><outline title="uncategorized" text="uncategorized"><outline title="{feeds[0].title}" text="{feeds[0].title}" type="rss" xmlUrl="{feeds[0].url}" /><outline title="{feeds[1].title}" text="{feeds[1].title}" type="rss" xmlUrl="{feeds[1].url}" /></outline></body></opml>'

        assert_compare_xml(content, expected_content.strip())


class TestExtractFeeds:

    def test(self, saved_feed: Feed, another_saved_feed: Feed) -> None:
        feeds = [saved_feed, another_saved_feed]
        feeds.sort(key=lambda feed: feed.title)

        content = create_opml(feeds)

        infos = extract_feeds(content)

        infos.sort(key=lambda info: info.title)

        assert infos[0] == FeedInfo(url=feeds[0].url,
       title=feeds[0].title,
       description="", entries=[],
       uid=url_to_uid(feeds[0].url))

        assert infos[1] == FeedInfo(url=feeds[1].url,
         title=feeds[1].title,
            description="", entries=[],
            uid=url_to_uid(feeds[1].url))
