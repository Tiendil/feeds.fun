import asyncio
import uuid

import typer

from ffun.application.application import with_app
from ffun.domain.entities import FeedId
from ffun.feeds_links.domain import unlink_feeds_from_all_users

cli_app = typer.Typer()


async def run_unlink(feed_ids: list[FeedId]) -> None:
    async with with_app():
        await unlink_feeds_from_all_users(feed_ids)


@cli_app.command()  # type: ignore
def unlink(feed_ids: list[uuid.UUID]) -> None:
    asyncio.run(run_unlink([FeedId(feed_id) for feed_id in feed_ids]))
