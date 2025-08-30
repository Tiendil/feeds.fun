from ffun.domain.entities import TagUid, TagUidPart


# TODO: tests
def uid_to_parts(uid: TagUid) -> list[TagUidPart]:
    if not uid:
        return []
    return [TagUidPart(part) for part in uid.split("-")]


# TODO: tests
def dashes_for_tag_part(text: str) -> str:
    if not text:
        # TODO: custome error
        raise NotImplementedError("Replacement text cannot be empty")

    if text[0] != "-":
        text = "-" + text

    if text[-1] != "-":
        text = text + "-"

    return text.lower()
