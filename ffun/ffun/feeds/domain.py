

from . import operations
from .entities import Feed
from .parsers.feedly import extract_feeds


def parse_opml(data: str) -> list[Feed]:
    return extract_feeds(data)


save_feeds = operations.save_feeds
