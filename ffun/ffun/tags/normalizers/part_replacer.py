from ffun.domain.entities import TagUid
from ffun.ontology.entities import NormalizationMode, RawTag
from ffun.tags import utils
from ffun.tags.entities import TagInNormalization
from ffun.tags.normalizers import base


class Normalizer(base.Normalizer):
    """Replace parts of tag uids based on a replacements dictionary.

    Example: "my-set-up-guide" with replacements {"set-up": "setup"} -> "my-setup-guide"

    Tries to apply each replacement once, if multiple replacements are possible multiple new tags are generated.

    Remember, that processing of new tags will begin from the first normalizer again
    => this normalizer still can be applied multiple times if needed.
    """

    __slots__ = ("replacements",)

    def __init__(self, replacements: dict[str, str]) -> None:
        self.replacements = {
            utils.dashes_for_tag_part(k): utils.dashes_for_tag_part(v) for k, v in replacements.items()
        }

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[RawTag]]:  # noqa: CCR001
        if not tag.uid:
            return False, []

        source_uid = f"-{tag.uid}-"

        new_uids = set()

        for replace_from, replace_to in self.replacements.items():
            if replace_from not in source_uid:
                continue

            processed_uid = source_uid

            while processed_uid != (new_uid := processed_uid.replace(replace_from, replace_to, count=1)):
                processed_uid = new_uid

            new_uids.add(TagUid(processed_uid.strip("-")))

        if not new_uids:
            return True, []

        new_tags = [
            RawTag(
                raw_uid=uid,
                normalization=NormalizationMode.raw,
                link=tag.link,
                categories=set(tag.categories),
            )
            for uid in new_uids
        ]

        return False, new_tags
