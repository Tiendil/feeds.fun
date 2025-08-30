from typing import Iterable

from ffun.ontology.entities import NormalizedTag, RawTag
from ffun.domain.entities import TagUid, TagUidPart
from ffun.tags import converters, utils
from ffun.tags.entities import TagInNormalization, NormalizerType
from ffun.tags.normalizers import Normalizer, normalizers



def prepare_for_normalization(tag: RawTag) -> TagInNormalization:
    return TagInNormalization(
        uid=tag.raw_uid,
        parts=utils.uid_to_parts(tag.raw_uid),

        preserve=tag.preserve,

        name=tag.name,
        link=tag.link,
        categories=set(tag.categories)
    )


# TODO: tests
# TODO: add missed tags
# TODO: we should copy preserve tags and process it as non-preserve? or not?
# TODO: look at most common parts of tags
# TODO: look at most common duplicates like `start-up` and `startup`, `login` and `log-in`, etc.
async def normalize(raw_tags: Iterable[RawTag]) -> list[NormalizedTag]:  # noqa: CCR001
    normalized_uids = {converters.normalize(tag) for tag in raw_tags}

    tags_to_process = {uid: prepare_for_normalization(TagUid(uid)) for uid in normalized_uids}

    processed_tags = set()
    normalized_tags = []

    while tags_to_process:
        tag = tags_to_process.popitem()[1]

        if tag.uid in processed_tags:
            continue

        processed_tags.add(tag.uid)

        for info in normalizers:
            can_continue, new_tags = await info.normalizer.normalize(tag)

            for new_tag in new_tags:
                if new_tag.uid in processed_tags or new_tag.uid in tags_to_process:
                    continue

                tags_to_process[new_tag.uid] = new_tag

            if not can_continue and not tag.preserve:
                tag = None
                break

        if tag is None:
            continue

        normalized_tag = NormalizedTag(
            uid=tag.uid,
            name=tag.name,
            link=tag.link,
            categories=tag.categories,
        )

        normalized_tags.append(normalized_tag)

    return normalized_tags
