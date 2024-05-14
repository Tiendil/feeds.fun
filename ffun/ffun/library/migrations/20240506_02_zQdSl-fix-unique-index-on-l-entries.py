"""
fix-unique-index-on-l-entries
"""

from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from yoyo import step

__depends__ = {"20240506_01_My4vi-remove-duplicated-entries-from-feeds"}


index = "l_entries_feed_id_external_id_key"


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor(row_factory=dict_row)

    cursor.execute(f"DROP INDEX {index}")
    cursor.execute(f"CREATE UNIQUE INDEX {index} ON l_entries (feed_id, external_id)")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor(row_factory=dict_row)

    cursor.execute(f"DROP INDEX {index}")
    cursor.execute(f"CREATE INDEX {index} ON l_entries (feed_id, external_id)")


steps = [step(apply_step, rollback_step)]
