import httpx
from ffun.feeds.entities import Feed
from ffun.library.entities import Entry
from ffun.parsers.domain import parse_feed


async def load_feed(feed: Feed) -> list[Entry]:

    async with httpx.AsyncClient() as client:
        response = await client.get(feed.url, follow_redirects=True)

    content = response.content.decode(response.encoding)

    return parse_feed(feed.id, content)
