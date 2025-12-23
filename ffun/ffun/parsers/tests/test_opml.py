import pytest

from ffun.core.tests.helpers import assert_compare_xml
from ffun.domain.urls import str_to_feed_url, url_to_uid
from ffun.feeds.entities import Feed
from ffun.parsers import errors
from ffun.parsers.entities import FeedInfo
from ffun.parsers.opml import _extract_body, create_opml, extract_feeds


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

    def test_opml_with_no_head(self) -> None:
        content = """
<opml version="2.0">
<body>
  <outline text="Subscriptions" title="Subscriptions">
    <outline type="rss" xmlUrl='https://example.com/feed' />
  </outline>
</body>
</opml>
        """

        infos = extract_feeds(content)

        expected_url = str_to_feed_url("https://example.com/feed")

        assert len(infos) == 1
        assert infos[0] == FeedInfo(
            url=expected_url,
            title="",
            description="",
            entries=[],
            uid=url_to_uid(expected_url),
        )

    def test_opml_with_no_type_attribute(self) -> None:
        content = """
<opml version="2.0">
<head>
  <title>My Subscriptions</title>
</head>
<body>
  <outline text="Subscriptions" title="Subscriptions">
    <outline xmlUrl='https://example.com/feed' />
  </outline>
</body>
</opml>
        """

        infos = extract_feeds(content)

        expected_url = str_to_feed_url("https://example.com/feed")

        assert len(infos) == 1
        assert infos[0] == FeedInfo(
            url=expected_url,
            title="",
            description="",
            entries=[],
            uid=url_to_uid(expected_url),
        )

    def test_opml_with_wrong_type_case(self) -> None:
        content = """
<opml version="2.0">
<head>
  <title>My Subscriptions</title>
</head>
<body>
  <outline text="Subscriptions" title="Subscriptions">
    <outline type="RsS" xmlUrl='https://example.com/feed' />
  </outline>
</body>
</opml>
        """

        infos = extract_feeds(content)

        expected_url = str_to_feed_url("https://example.com/feed")

        assert len(infos) == 1
        assert infos[0] == FeedInfo(
            url=expected_url,
            title="",
            description="",
            entries=[],
            uid=url_to_uid(expected_url),
        )


class TestExtractBody:

    def test_no_content(self) -> None:
        with pytest.raises(errors.OPMLParsingError):
            _extract_body("")

    def test_not_well_formed(self) -> None:
        content = """
<?xml version="1.0" encoding="UTF-8"?>
<root>
    <items>
        <item>
            This line contains an invalid token & here
        </item>
    </items>
</root>
        """.strip()

        with pytest.raises(errors.OPMLParsingError):
            _extract_body(content)

    def test_no_opml_root(self) -> None:
        content = """
        <?xml version="1.0" encoding="UTF-8"?>
        <body>
        <outline text="General News" title="General News">
            <outline type="rss"
                     text="BBC News - World"
                     title="BBC News"
                     xmlUrl="http://feeds.bbci.co.uk/news/rss.xml"
                     htmlUrl="https://www.bbc.com/news"/>
            <outline type="rss"
                     text="The New York Times - Home"
                     title="NYT"
                     xmlUrl="https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"
                     htmlUrl="https://www.nytimes.com"/>
        </outline>
        </body>
        """.strip()

        with pytest.raises(errors.OPMLNoRoot):
            _extract_body(content)

    def test_no_body(self) -> None:
        content = """
        <?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
        <head>
            <title>My Subscriptions</title>
        </head>
        </opml>
        """.strip()

        with pytest.raises(errors.OPMLNoBody):
            _extract_body(content)

    def test_success(self) -> None:
        content = """
        <?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
        <head>
            <title>My Subscriptions</title>
        </head>
        <body>
            <outline text="General News" title="General News">
                <outline type="rss"
                         text="BBC News - World"
                         title="BBC News"
                         xmlUrl="http://feeds.bbci.co.uk/news/rss.xml"
                         htmlUrl="https://www.bbc.com/news"/>
                <outline type="rss"
                         text="The New York Times - Home"
                         title="NYT"
                         xmlUrl="https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml"
                         htmlUrl="https://www.nytimes.com"/>
            </outline>
        </body>
        </opml>
        """.strip()

        body = _extract_body(content)

        assert body.tag == "body"
