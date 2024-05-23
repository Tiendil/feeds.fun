import asyncio
import datetime
from typing import Any

from ffun.core import logging, utils
from ffun.core.background_tasks import InfiniteTask
from ffun.feeds import domain as f_domain
from ffun.loader import domain
from ffun.loader.settings import settings

logger = logging.get_module_logger()


# TODO: tests
class FeedsLoader(InfiniteTask):
    __slots__ = ("_loaders_number", "_last_proxies_check")

    def __init__(self, loaders_number: int = settings.loaders_number, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._loaders_number = loaders_number
        self._last_proxies_check = datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)

    async def single_run(self) -> None:
        if utils.now() - self._last_proxies_check > settings.proxy_available_check_period:
            await domain.check_proxies_availability()
            self._last_proxies_check = utils.now()

        feeds = await f_domain.get_next_feeds_to_load(
            number=self._loaders_number, loaded_before=datetime.datetime.utcnow() - settings.minimum_period
        )

        tasks = [domain.process_feed(feed=feed) for feed in feeds]

        await asyncio.gather(*tasks, return_exceptions=True)
