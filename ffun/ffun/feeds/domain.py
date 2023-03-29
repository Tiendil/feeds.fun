

from .entities import Feed
from .operations import save_feeds
from .parsers.feedly import extract_feeds


async def parse_opml(data: str) -> list[Feed]:
    feeds = extract_feeds(data)

    await save_feeds(feeds)
