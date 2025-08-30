from ffun.domain.entities import TagUid, TagUidPart


# TODO: tests
def uid_to_parts(uid: TagUid) -> list[TagUidPart]:
    if not uid:
        return []
    return [TagUidPart(part) for part in uid.split("-")]
