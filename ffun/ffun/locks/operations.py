import psycopg

from ffun.core.postgresql import ExecuteType
from ffun.locks import errors


async def acquire(execute: ExecuteType, lock_kind: str, lock_key: str) -> None:
    sql = """
    INSERT INTO lk_locks (lock_kind, lock_key)
    VALUES (%(lock_kind)s, %(lock_key)s)
    """

    try:
        await execute(sql, {"lock_kind": lock_kind, "lock_key": lock_key})
    except psycopg.errors.UniqueViolation as exception:
        raise errors.LockInvariantViolation(
            lock_kind=lock_kind,
            lock_key=lock_key,
            reason="an acquisition row already exists",
        ) from exception


async def release(execute: ExecuteType, lock_kind: str, lock_key: str) -> None:
    sql = """
    DELETE FROM lk_locks
    WHERE lock_kind = %(lock_kind)s
      AND lock_key = %(lock_key)s
    RETURNING lock_kind
    """

    rows = await execute(sql, {"lock_kind": lock_kind, "lock_key": lock_key})

    if len(rows) != 1:
        raise errors.LockInvariantViolation(
            lock_kind=lock_kind,
            lock_key=lock_key,
            reason=f"expected to delete one acquisition row, deleted {len(rows)}",
        )
