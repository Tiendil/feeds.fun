from ffun.domain.entities import TagUid, TagUidPart


def uid_to_parts(uid: TagUid) -> list[TagUidPart]:
    return [TagUidPart(part) for part in uid.split("-")]
