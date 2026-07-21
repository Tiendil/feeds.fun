import uuid

from ffun.locks.entities import LockKind


def new_lock_kind(prefix: str = "test_lock") -> LockKind:
    return LockKind(f"{prefix}_{uuid.uuid4().hex}")
