from ffun.tags import utils
from ffun.tags.entities import TagInNormalization
from ffun.tags.normalizers import base


class Normalizer(base.Normalizer):
    """Split tag into multiple parts based on a replacements dictionary.

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

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[TagInNormalization]]:  # noqa: CCR001
        if not tag.uid:
            return False, []

        new_uids = set()

        for separator in self.separators:
            if separator not in tag.uid:
                continue

            for part in tag.uid.split(separator):
                part = part.strip("-")

                if part:
                    new_uids.add(part)

        if not new_uids:
            return True, []

        new_tags = [tag.replace(uid=uid, parts=utils.uid_to_parts(uid), preserve=False, name=None) for uid in new_uids]

        return False, new_tags
