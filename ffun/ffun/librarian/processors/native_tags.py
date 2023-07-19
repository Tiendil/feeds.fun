from ffun.library.entities import Entry
from ffun.ontology.entities import ProcessorTag, TagCategory

from . import base


class Processor(base.Processor):
    __slots__ = ()

    async def process(self, entry: Entry) -> list[ProcessorTag]:
        tags: list[ProcessorTag] = []

        for external_tag in entry.external_tags:
            tags.append(ProcessorTag(raw_uid=external_tag, categories={TagCategory.feed_tag}))

        return tags
