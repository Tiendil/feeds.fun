from ffun.tags.entities import TagInNormalization
from ffun.tags.normalizers.base import Normalizer


# TODO: tests
class PartBlacklistNormalizer(Normalizer):
    """Remove parts of tag uids that are in the blacklist.

    Example: "the-best-startup" with blacklist {"the"} -> "best-startup"
    """

    __slots__ = ("blacklist",)

    def __init__(self, blacklist: set[str]) -> None:
        self.blacklist = blacklist

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[TagInNormalization]]:
        new_parts = [part for part in tag.parts if part.part not in self.blacklist]

        if len(new_parts) == len(tag.parts):
            return True, []

        if not new_parts:
            return False, []

        new_uid = "-".join(part.part for part in new_parts)

        new_tag = tag.replace(uid=new_uid, parts=new_parts, name=None)

        return True, [new_tag]
