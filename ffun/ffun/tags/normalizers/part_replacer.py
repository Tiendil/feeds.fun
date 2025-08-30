from ffun.tags import utils
from ffun.tags.entities import TagInNormalization
from ffun.tags.normalizers.base import Normalizer


def prepare_replacement(text: str) -> str:
    if not text:
        # TODO: custome error
        raise NotImplementedError("Replacement text cannot be empty")

    if text[0] != "-":
        text = "-" + text

    if text[-1] != "-":
        text = text + "-"

    return text.lower()


# TODO: tests
class PartBlacklistNormalizer(Normalizer):
    """Replace parts of tag uids based on a replacements dictionary.

    Example: "my-set-up-guide" with replacements {"set-up": "setup"} -> "my-setup-guide"

    Tries to apply each replacement once, if multiple replacements are possible multiple new tags are generated.

    Remember, that processing of new tags will begin from the first normalizer again
    => this normalizer still can be applied multiple times if needed.
    """

    __slots__ = ("replacements",)

    def __init__(self, replacements: dict[str, str]) -> None:
        self.replacements = {prepare_replacement(k): prepare_replacement(v) for k, v in replacements.items()}

    async def normalize(self, tag: TagInNormalization) -> tuple[bool, list[TagInNormalization]]:
        source_uid = f"-{tag.uid}-"

        new_uids = set()

        for replace_from, replace_to in self.replacements.items():
            new_uid = source_uid.replace(replace_from, replace_to)

            if new_uid != source_uid:
                new_uids.add(new_uid[1:-1])

        if not new_uids:
            return True, []

        new_tags = [tag.replace(uid=uid, parts=utils.uid_to_parts(uid), name=None) for uid in new_uids]
        return False, new_tags
