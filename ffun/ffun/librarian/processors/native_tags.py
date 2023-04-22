from ffun.library.entities import Entry

from . import base


# TODO: normalize tags
class Processor(base.Processor):
    __slots__ = ()

    async def process(self, entry: Entry) -> set[str]:
        return set(entry.external_tags)
