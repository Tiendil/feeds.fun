import asyncio
import uuid

from ffun.application.application import with_app
from ffun.cli.application import app
from ffun.core import logging
from ffun.meta import domain as m_domain

logger = logging.get_module_logger()


async def run(base_feed_id: uuid.UUID, merged_feed_id: uuid.UUID) -> None:
    async with with_app():
        await m_domain.merge_feeds(base_feed_id, merged_feed_id)


@app.command()
def merge_feeds(base_feed_id: uuid.UUID, merged_feed_id: uuid.UUID) -> None:
    asyncio.run(run(base_feed_id, merged_feed_id))
