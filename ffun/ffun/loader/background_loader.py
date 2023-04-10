
import datetime
import logging

from ffun.core.background_tasks import InfiniteTask
from ffun.feeds import domain as f_domain
from ffun.library import domain as l_domain
from ffun.loader import domain
from ffun.loader.settings import settings

logger = logging.getLogger(__name__)


class FeedsLoader(InfiniteTask):
    __slots__ = ('_loaders_number',)

    def __init__(self, loaders_number: int = 1, **kwargs) -> None:
        super().__init__(**kwargs)
        self._loaders_number = loaders_number

    async def single_run(self) -> None:
        feeds = await f_domain.get_next_feeds_to_load(number=self._loaders_number,
                                                      loaded_before=datetime.datetime.now() - settings.minimum_period)

        # TODO: run concurrently
        for feed in feeds:
            logger.info("Loading feed %s", feed)

            entries = await domain.load_feed(feed=feed)

            # TODO: store only new entries
            await l_domain.catalog_entries(entries=entries)

            await f_domain.mark_feed_as_loaded(feed.id)

            logger.info("Loaded %s entries", len(entries))
