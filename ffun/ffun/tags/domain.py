from typing import Iterable

from ffun.ontology.entities import NormalizedTag, RawTag
from ffun.tags import converters, utils
from ffun.tags.entities import NormalizationMode, TagInNormalization, TagCategory
from ffun.tags.normalizers import NormalizerInfo, normalizers


# TODO: move tests from test_entities to test_domain
# Here is going some complicated unclear logic:
# - normalizers work with TagInNormalization
# - TagInNormalization should define how it should be processed by normalizers
# - There are two options: define explicitly or implicitly (derive from categories)
# - It may look like a good idea to define it explicitly, so we could have a normalizer
#   that could say "I produce this new tag which should be processed as raw/preserve/final"
# - But this approach leads to uncertainty when we doing re-normalization of tags in the database
#   because we don't store the final normalization mode in the database
#   (and it may be wrong in case of re-normalization)
#   So, on re-normalization we use tag categories to derive the mode (again)
#   We also use RawTag, not TagInNormalization as a result of running a normalizer.
# - That's why it seems more consistent to try building logic of normalizators around categories only
#   To be consistent in the whole system
# => We expect, that normalizer, if it requires, will be able to set new categories for the tags it produces
#    For example, there may be a normalizer that detects network domains in free-form tags
def mode_from_categories(categories: set[TagCategory]) -> NormalizationMode:  # noqa: CCR001
    # The order of checks is important here

    if TagCategory.network_domain in categories:
        return NormalizationMode.final

    if TagCategory.special in categories:
        return NormalizationMode.final

    # We do not normalize native feed tags, because:
    # - We have no control over the logic that assigns them
    # - Sometimes they are (semi-)technical (special terms, domain names, codes)
    # - Sometimes they are very specific, like r-sideproject (for subreddits)
    #   and we don't want to create a duplicated tag like r-sideprojects that actually has no meaning
    if TagCategory.feed_tag in categories:
        return NormalizationMode.final

    if TagCategory.free_form in categories:
        return NormalizationMode.raw

    if TagCategory.test_final in categories:
        return NormalizationMode.final

    if TagCategory.test_preserve in categories:
        return NormalizationMode.preserve

    if TagCategory.test_raw in categories:
        return NormalizationMode.raw

    raise NotImplementedError(f"Tag with unknown categories: {categories}")


def prepare_for_normalization(tag: RawTag) -> TagInNormalization:
    # 1. We better normalize uids even for final tags:
    #    - In case all works well, they will remain unchanged
    #    - In case of some issues, we'll stop an error propagation here
    # 2. We keep text normalization outside of the normalizers list, since:
    #    - it is a common step for all tags, and we don't want to repeat it in each normalizer
    #    - it is not a normalizer itself, but rather a preparation step for normalizers,
    #      so it is better to keep it outside of the normalizers list. For example,
    #      we fill .parts field on the base of normalized uid.

    # TODO: add tests that mode is detected correctly, if there are no test for it yet
    mode = mode_from_categories(tag.categories)

    # TODO: add test to check allow_unicode true|false behavior
    # We do not allow unicode characters in raw tags, they must be pure ASCII. At list for now.
    # It can be changed in https://github.com/Tiendil/feeds.fun/issues/348
    allow_unicode = (mode != NormalizationMode.raw)

    uid = converters.normalize(tag.raw_uid, allow_unicode=allow_unicode)

    return TagInNormalization(
        uid=uid,
        parts=utils.uid_to_parts(uid),
        link=tag.link,
        categories=set(tag.categories),
        mode=mode,
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
