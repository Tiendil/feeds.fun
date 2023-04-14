import logging

from ffun.library.entities import Entry

from . import base

logger = logging.getLogger(__name__)


# TODO: normalize tags
class Processor(base.Processor):
    __slots__ = ()

    async def process(self, entry: Entry) -> set[str]:
        return set(entry.external_tags)
