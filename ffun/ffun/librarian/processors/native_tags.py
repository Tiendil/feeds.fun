from ffun.librarian.processors import base
from ffun.library.entities import Entry
from ffun.ontology.entities import NormalizationMode, RawTag, TagCategory


class Processor(base.Processor):
    __slots__ = ()

    async def process(self, entry: Entry) -> list[RawTag]:
        tags: list[RawTag] = []

        for external_tag in entry.external_tags:
            tags.append(
                RawTag(
                    raw_uid=external_tag, normalization=NormalizationMode.preserve, categories={TagCategory.feed_tag}
                )
            )

        return tags
