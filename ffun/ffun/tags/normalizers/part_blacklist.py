from ffun.ontology.entities import NormalizationMode, RawTag
from ffun.tags.entities import TagInNormalization
from ffun.tags.normalizers import base


class Normalizer(base.Normalizer):
    """Remove parts of tag uids that are in the blacklist.

    Example: "the-best-startup" with blacklist {"the"} -> "best-startup"
    """

    __slots__ = ("blacklist",)

    def __init__(self, blacklist: set[str]) -> None:
        self.blacklist = blacklist

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[RawTag]]:
        if not tag.parts:
            return False, []

        new_parts = [part for part in tag.parts if part not in self.blacklist]

        if len(new_parts) == len(tag.parts):
            return True, []

        if not new_parts:
            return False, []

        new_uid = "-".join(new_parts)

        return False, [
            RawTag(
                raw_uid=new_uid,
                normalization=NormalizationMode.raw,
                link=tag.link,
                categories=set(tag.categories),
            )
        ]
