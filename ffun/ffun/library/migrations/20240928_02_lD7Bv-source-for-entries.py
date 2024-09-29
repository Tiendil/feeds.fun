"""
source-for-entries
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20240506_02_zQdSl-fix-unique-index-on-l-entries", "20240928_01_OEKOr-source-table"}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("ALTER TABLE l_entries ADD COLUMN source_id UUID NULL DEFAULT NULL")

    cursor.execute(
        "UPDATE l_entries SET source_id = f_feeds.source_id FROM f_feeds WHERE l_entries.feed_id = f_feeds.id"
    )

    cursor.execute("ALTER TABLE l_entries ALTER COLUMN source_id SET NOT NULL")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("ALTER TABLE l_entries DROP COLUMN source_id")


steps = [step(apply_step, rollback_step)]
