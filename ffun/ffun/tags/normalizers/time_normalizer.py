from ffun.domain.entities import TagUid
from ffun.ontology.entities import NormalizationMode, RawTag
from ffun.tags import utils
from ffun.tags.entities import TagInNormalization
from ffun.tags.normalizers import base


def guard_1_ends_with_digit(part: str) -> bool:
    return part[-1].isdigit()


# TODO: comment/mark application of each guard
# TODO: maybe organize guards in a lists, if it makes sense
class Normalizer(base.Normalizer):
    """Normalizes time of tag parts.

    The primary heuristic:

    - pluralize the last part of the tag if it can be pluralized;
    - singularize all other parts of the tag if they can be singularized;
    - use guard to process corner cases.

    Guards:

    1. If the part ends with a digit, do not change it.
    """

    __slots__ = ('_tail_cache', '_head_cache')

    def __init__(self) -> None:
        self._tail_cache = {}
        self._head_cache = {}

    def _normalize_tail_part(self, part: str) -> str:
        if guard_1_ends_with_digit(part):
            return part

        return part

    def normalize_tail_part(self, part: str) -> str:
        if part in self._tail_cache:
            return self._tail_cache[part]

        normalized_part = self._normalize_tail_part(part)

        self._tail_cache[part] = normalized_part

        return normalized_part

    def _normalize_head_part(self, part: str) -> str:
        if guard_1_ends_with_digit(part):
            return part

        return part

    def normalize_head_part(self, part: str) -> str:
        if part in self._head_cache:
            return self._head_cache[part]

        normalized_part = self._normalize_head_part(part)

        self._head_cache[part] = normalized_part

        return normalized_part

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[RawTag]]:  # noqa: CCR001
        if not tag.uid:
            return False, []

        last_part = self.normalize_tail_part(tag.parts[-1])

        head_parts = [self.normalize_head_part(part) for part in tag.parts[:-1]]

        new_uid = '-'.join([*head_parts, last_part])

        if new_uid == tag.uid:
            return True, []

        new_tag = RawTag(
            raw_uid=new_uid,
            normalization=NormalizationMode.raw,
            link=tag.link,
            categories=set(tag.categories),
        )

        return False, [new_tag]
