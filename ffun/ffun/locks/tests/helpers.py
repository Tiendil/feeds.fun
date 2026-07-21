from typing import cast

from ffun.core.postgresql import ExecuteType


async def count_acquisition_rows(execute: ExecuteType) -> int:
    rows = cast(
        list[dict[str, int]],
        await execute(
            """
            SELECT count(*) AS number
            FROM lk_locks
            """
        ),
    )
    return rows[0]["number"]


async def load_acquisition_rows(
    execute: ExecuteType,
    lock_kind: str,
    lock_key: str | None = None,
) -> list[dict[str, object]]:
    if lock_key is None:
        sql = """
        SELECT lock_kind, lock_key
        FROM lk_locks
        WHERE lock_kind = %(lock_kind)s
        ORDER BY lock_key
        """
        arguments = {"lock_kind": lock_kind}
    else:
        sql = """
        SELECT lock_kind, lock_key
        FROM lk_locks
        WHERE lock_kind = %(lock_kind)s
          AND lock_key = %(lock_key)s
        """
        arguments = {"lock_kind": lock_kind, "lock_key": lock_key}

    return cast(list[dict[str, object]], await execute(sql, arguments))
