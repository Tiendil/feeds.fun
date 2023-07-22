from ffun.feeds.entities import Feed

from . import feed
from .entities import FeedInfo
from .feedly import extract_feeds


def parse_opml(data: str) -> list[FeedInfo]:
    return extract_feeds(data)


parse_feed = feed.parse_feed
