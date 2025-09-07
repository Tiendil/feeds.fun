from typing import Iterable

from ffun.ontology.entities import NormalizedTag, RawTag
from ffun.tags import converters, utils
from ffun.tags.entities import TagInNormalization
from ffun.tags.normalizers import normalizers


def prepare_for_normalization(tag: RawTag) -> TagInNormalization:
    uid = converters.normalize(tag.raw_uid)

    return TagInNormalization(
        uid=uid,
        parts=utils.uid_to_parts(uid),
        preserve=tag.preserve,
        link=tag.link,
        categories=set(tag.categories),
    )


# TODO: tests
async def apply_normalizers(tag: TagInNormalization) -> tuple[bool, list[RawTag]]:
    all_new_tags = []

    for info in normalizers:
        tag_valid, new_tags = await info.normalizer.normalize(tag)

        all_new_tags.extend(new_tags)

        if not tag_valid:
            return (False or tag.preserve, all_new_tags)

    return (True, all_new_tags)


# TODO: tests
# TODO: measure impact of each normalizer
# TODO: check what if tag.name is None
# TODO: fill configs
async def normalize(raw_tags: Iterable[RawTag]) -> list[NormalizedTag]:  # noqa: CCR001

    tags_to_process = {tag.uid: tag for tag in [prepare_for_normalization(raw_tag) for raw_tag in raw_tags]}

    processed_tags = set()
    normalized_tags = []

    tag: TagInNormalization | None

    while tags_to_process:
        tag = tags_to_process.popitem()[1]

        if tag.uid in processed_tags:
            continue

        processed_tags.add(tag.uid)

        tag_valid, new_raw_tags = await apply_normalizers(tag)

        for new_raw_tag in new_raw_tags:
            new_tag = prepare_for_normalization(new_raw_tag)

            if new_tag.uid in processed_tags or new_tag.uid in tags_to_process:
                continue

            # Theoretically, normalizers can produce malformed tags.
            # We protecting against it by running normalization from scratch for each new tag.
            tags_to_process[new_tag.uid] = new_tag

        if not tag_valid:
            continue

        normalized_tag = NormalizedTag(
            uid=tag.uid,
            link=tag.link,
            categories=tag.categories,
        )

        normalized_tags.append(normalized_tag)

    return normalized_tags
