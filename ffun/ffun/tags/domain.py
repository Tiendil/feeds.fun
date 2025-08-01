from typing import Iterable

from ffun.ontology.entities import NormalizedTag, RawTag
from ffun.tags import converters


async def normalize(raw_tags: Iterable[RawTag]) -> list[NormalizedTag]:
    normalized_tags = []
    existed_tags = set()

    for raw_tag in raw_tags:
        uid = converters.normalize(raw_tag.raw_uid)

        if uid in existed_tags:
            continue

        existed_tags.add(uid)

        normalized_tag = NormalizedTag(
            uid=uid,
            name=raw_tag.name,
            link=raw_tag.link,
            categories=raw_tag.categories,
        )

        normalized_tags.append(normalized_tag)

    return normalized_tags
