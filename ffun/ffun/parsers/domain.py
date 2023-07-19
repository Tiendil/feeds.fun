from ffun.feeds.entities import Feed

from . import feed
from .feedly import extract_feeds


def parse_opml(data: str) -> list[Feed]:
    return extract_feeds(data)


parse_feed = feed.parse_feed
