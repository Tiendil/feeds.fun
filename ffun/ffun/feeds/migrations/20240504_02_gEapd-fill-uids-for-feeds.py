"""
fill-uids-for-feeds
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20240504_01_vBDVJ-column-for-feed-unique-id"}


def get_feeds(cursor: Any) -> list[dict[str, Any]]:
    cursor.execute("SELECT id, url FROM f_feeds")

    return [{"id": row[0], "url": row[1]} for row in cursor.fetchall()]


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    pass


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    pass


steps = [step(apply_step, rollback_step)]
