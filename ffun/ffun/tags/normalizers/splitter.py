from ffun.ontology.entities import NormalizationMode, RawTag
from ffun.tags.entities import TagInNormalization
from ffun.tags.normalizers import base


class Normalizer(base.Normalizer):
    """Split tag into TWO parts based on a replacements dictionary.

    Examples:
    - `rest-api-for-graph-processing` by `for` -> `rest-api` & `graph-processing`
    - `social-media-impact-on-innovation` by `impact-on` -> `social-media-impact` & `innovation`
    - `artistic-expression-through-artistic-skills` by `through` -> `artistic-expression` & `artistic-skills`

    Tries to apply each split once, if multiple replacements are possible multiple new tags are generated.

    Remember, that processing of new tags will begin from the first normalize again
    => this normalize still can be applied multiple times if needed.
    """

    __slots__ = ("separators",)

    def __init__(self, separators: list[str]) -> None:
        self.separators = separators

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[RawTag]]:  # noqa: CCR001
        base_uid = tag.uid
        base_len = len(base_uid)

        if not base_uid:
            return False, []

        new_uids = set()

        for separator in self.separators:
            if separator not in base_uid:
                continue

            separator_len = len(separator)

            find_start = 0

            while (sep_start := base_uid.find(separator, find_start)) != -1:
                find_start = sep_start + 1

                ##########################################################
                # check that we cut tag only by full part, not inside part
                if sep_start > 0 and base_uid[sep_start - 1] != "-":
                    continue

                if sep_start + separator_len < base_len and base_uid[sep_start + separator_len] != "-":
                    continue
                ##########################################################

                for part in (base_uid[0:sep_start], base_uid[sep_start + len(separator) :]):
                    part = part.strip("-")

                    if part:
                        new_uids.add(part)

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
