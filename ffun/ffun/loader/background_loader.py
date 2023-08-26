import asyncio
import datetime
from typing import Any

from ffun.core import logging
from ffun.core.background_tasks import InfiniteTask
from ffun.feeds import domain as f_domain
from ffun.loader import domain
from ffun.loader.settings import settings

logger = logging.get_module_logger()


class FeedsLoader(InfiniteTask):
    __slots__ = ("_loaders_number",)

    def __init__(self, loaders_number: int = settings.loaders_number, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._loaders_number = loaders_number

    async def single_run(self) -> None:
        feeds = await f_domain.get_next_feeds_to_load(
            number=self._loaders_number, loaded_before=datetime.datetime.utcnow() - settings.minimum_period
        )

        tasks = [domain.process_feed(feed=feed) for feed in feeds]

        await asyncio.gather(*tasks, return_exceptions=True)
