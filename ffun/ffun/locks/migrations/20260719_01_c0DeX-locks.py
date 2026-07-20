"""
locks
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()


sql_create_locks = """
-- Ephemeral exact-key rows used to coordinate holder transactions.
CREATE TABLE lk_locks (
    lock_kind TEXT COLLATE "C" NOT NULL,
    lock_key TEXT COLLATE "C" NOT NULL,
    PRIMARY KEY (lock_kind, lock_key)
)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_locks)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE lk_locks")


steps = [step(apply_step, rollback_step)]
