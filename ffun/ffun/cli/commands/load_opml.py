
import asyncio
import pathlib

from ffun.application.application import with_app
from ffun.feeds import domain as f_domain
from ffun.feeds.entities import Feed

from ..application import app


async def run(feeds: list[Feed]) -> None:
    async with with_app():
        await f_domain.save_feeds(feeds)


@app.command()
def load_opml(path: pathlib.Path) -> None:

    with path.open() as f:
        raw_data = f.read()

    feeds = f_domain.parse_opml(raw_data)

    asyncio.run(run(feeds))
