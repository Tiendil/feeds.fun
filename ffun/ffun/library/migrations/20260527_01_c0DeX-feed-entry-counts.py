"""
feed-entry-counts
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20260513_01_Km3Qx-updated-at-for-feed-entry-links"}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE l_feed_entries_count (
            feed_id UUID NOT NULL,
            date DATE NOT NULL,
            entries INTEGER NOT NULL,

            PRIMARY KEY (feed_id, date)
        )
        """
    )


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE l_feed_entries_count")


steps = [step(apply_step, rollback_step)]
