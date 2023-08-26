from ffun.parsers import feed
from ffun.parsers.entities import FeedInfo
from ffun.parsers.feedly import extract_feeds


def parse_opml(data: str) -> list[FeedInfo]:
    return extract_feeds(data)


parse_feed = feed.parse_feed
