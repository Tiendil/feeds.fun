"""
updated-at-for-feed-entry-links
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20260415_01_DdxK9-references-column"}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(
        "ALTER TABLE l_feeds_to_entries ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()"
    )


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE l_feeds_to_entries DROP COLUMN updated_at")


steps = [step(apply_step, rollback_step)]
