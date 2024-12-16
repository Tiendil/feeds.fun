from ffun.core.tests.helpers import assert_compare_xml
from ffun.domain.urls import url_to_uid
from ffun.feeds.entities import Feed
from ffun.parsers.entities import FeedInfo
from ffun.parsers.opml import create_opml, extract_feeds


class TestCreateOpml:

    def test(self, saved_feed: Feed, another_saved_feed: Feed) -> None:

        feeds = [saved_feed, another_saved_feed]
        feeds.sort(key=lambda feed: feed.title if feed.title is not None else "")

        content = create_opml(feeds)

        expected_content = f'<opml version="2.0"><head><title>Your subscriptions in feeds.fun</title></head><body><outline title="uncategorized" text="uncategorized"><outline title="{feeds[0].title}" text="{feeds[0].title}" type="rss" xmlUrl="{feeds[0].url}" /><outline title="{feeds[1].title}" text="{feeds[1].title}" type="rss" xmlUrl="{feeds[1].url}" /></outline></body></opml>'  # noqa: E501

        assert_compare_xml(content, expected_content.strip())


class TestExtractFeeds:

    def test(self, saved_feed: Feed, another_saved_feed: Feed) -> None:
        feeds = [saved_feed, another_saved_feed]
        feeds.sort(key=lambda feed: feed.title if feed.title is not None else "")

        content = create_opml(feeds)

        infos = extract_feeds(content)

        infos.sort(key=lambda info: info.title)

        assert infos[0] == FeedInfo(
            url=feeds[0].url,
            title=feeds[0].title if feeds[0].title is not None else "",
            description="",
            entries=[],
            uid=url_to_uid(feeds[0].url),
        )

        assert infos[1] == FeedInfo(
            url=feeds[1].url,
            title=feeds[1].title if feeds[1].title is not None else "",
            description="",
            entries=[],
            uid=url_to_uid(feeds[1].url),
        )
