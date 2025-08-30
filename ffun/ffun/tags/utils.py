from ffun.domain.entities import TagUid, TagUidPart
from ffun.tags import errors


def uid_to_parts(uid: TagUid) -> list[TagUidPart]:
    if not uid:
        return []
    return [TagUidPart(part) for part in uid.split("-")]


def dashes_for_tag_part(text: str) -> str:
    if not text:
        raise errors.TagPartIsEmpty()

    if text[0] != "-":
        text = "-" + text

    if text[-1] != "-":
        text = text + "-"

    return text.lower()
