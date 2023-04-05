
import asyncio
import logging

from ffun.application.application import with_app
from ffun.librarian import domain as ln_domain

from ..application import app

logger = logging.getLogger(__name__)


async def run(processor_id: int) -> None:
    async with with_app():
        await ln_domain.process_new_entries(processor_id=processor_id)


@app.command()
def discover_tags(processor_id: int = 1) -> None:
    asyncio.run(run(processor_id=processor_id))
