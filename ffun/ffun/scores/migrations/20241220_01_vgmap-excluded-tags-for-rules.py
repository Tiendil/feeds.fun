"""
excluded-tags-for-rules
"""

from typing import Any, Iterable

from psycopg import Connection
from yoyo import step

__depends__ = {"20230813_01_l7qop-updated-at-field"}


def _key_from_tags(required_tags: Iterable[int], excluded_tags: Iterable[int]) -> str:
    return ",".join(map(str, required_tags)) + "|" + ",".join(map(str, excluded_tags))


def apply_step(conn: Connection[Any]) -> None:
    cursor = conn.cursor()

    cursor.execute("ALTER TABLE s_rules RENAME COLUMN tags TO required_tags")
    cursor.execute("ALTER TABLE s_rules ADD COLUMN excluded_tags BIGINT[] DEFAULT ARRAY[]::BIGINT[]")

    result = cursor.execute("SELECT id, required_tags FROM s_rules").fetchall()

    for row in result:
        cursor.execute(
            "UPDATE s_rules SET key = %(key)s, excluded_tags = ARRAY[]::BIGINT[] WHERE id = %(id)s",
            {"id": row[0], "key": _key_from_tags(row[1], [])},
        )

    cursor.execute("ALTER TABLE s_rules ALTER COLUMN excluded_tags SET NOT NULL")
    cursor.execute("ALTER TABLE s_rules ALTER COLUMN excluded_tags DROP DEFAULT")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("ALTER TABLE s_rules RENAME COLUMN required_tags TO tags")
    cursor.execute("ALTER TABLE s_rules DROP COLUMN excluded_tags")


steps = [step(apply_step, rollback_step)]
