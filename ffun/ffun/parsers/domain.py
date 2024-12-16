from ffun.parsers import feed
from ffun.parsers.entities import FeedInfo
from ffun.parsers import opml


def parse_opml(data: str) -> list[FeedInfo]:
    return opml.extract_feeds(data)


create_opml = opml.create_opml


parse_feed = feed.parse_feed
