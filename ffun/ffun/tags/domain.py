from typing import Iterable

from ffun.ontology.entities import NormalizationMode, NormalizedTag, RawTag
from ffun.tags import converters, utils
from ffun.tags.entities import TagInNormalization
from ffun.tags.normalizers import NormalizerInfo, normalizers


def prepare_for_normalization(tag: RawTag) -> TagInNormalization:
    # we better normalize uids even for final tags:
    # - In case all works well, they will remain unchanged
    # - In case of some issues, we'll stop an error propagation here
    uid = converters.normalize(tag.raw_uid)

    return TagInNormalization(
        uid=uid,
        parts=utils.uid_to_parts(uid),
        mode=tag.normalization,
        link=tag.link,
        categories=set(tag.categories),
    )


# TODO: we may want to cache chain of tags, to skip the whole normalizers operations
#       i.e. remember once that at the end tag @a-b-c produces tags @a-b, @a-c, @b-c and skip the whole
#       normalizers chain.
async def apply_normalizers(normalizers_: list[NormalizerInfo], tag: TagInNormalization) -> tuple[bool, list[RawTag]]:

    if tag.mode == NormalizationMode.final:
        return (True, [])

    all_new_tags = []

    for info in normalizers_:
        tag_valid, new_tags = await info.normalize(tag)

        all_new_tags.extend(new_tags)

        if not tag_valid and tag.mode == NormalizationMode.raw:
            return (False, all_new_tags)

    return (True, all_new_tags)


# Note: we should keep calls of prepare_for_normalization(...) in a single place, either here or in apply_normalizers
#       since we control duplicates by comparing normalized uids
#       we should keep calls to prepare_for_normalization(...) in the normalize(...) function
async def normalize(  # noqa: CCR001
    raw_tags: Iterable[RawTag], normalizers_: list[NormalizerInfo] | None = None
) -> list[NormalizedTag]:

    if normalizers_ is None:
        normalizers_ = normalizers

    tags_to_process = {tag.uid: tag for tag in [prepare_for_normalization(raw_tag) for raw_tag in raw_tags]}

    processed_tags = set()
    normalized_tags = []

    tag: TagInNormalization | None

    while tags_to_process:
        tag = tags_to_process.popitem()[1]

        if tag.uid in processed_tags:
            continue

        processed_tags.add(tag.uid)

        tag_valid, new_raw_tags = await apply_normalizers(normalizers_, tag)

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
