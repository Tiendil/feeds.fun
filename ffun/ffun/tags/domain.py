
from typing import Iterable
from ffun.ontology.entities import RawTag, NormalizedTag
from ffun.tags import converters


# TODO: add tests when start implementing the normalization logic
async def normalize(raw_tags: Iterable[RawTag]) -> list[NormalizedTag]:
    normalized_tags = []

    for raw_tag in raw_tags:
        normalized_tag = NormalizedTag(
            uid=converters.normalize(raw_tag.raw_uid),
            name=raw_tag.name,
            link=raw_tag.link,
            categories=raw_tag.categories,
        )
        normalized_tags.append(normalized_tag)

    return normalized_tags
