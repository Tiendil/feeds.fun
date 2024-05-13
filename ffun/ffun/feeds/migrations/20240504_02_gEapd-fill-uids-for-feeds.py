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
    # Generally, we should avoid importing from the main project in migrations
    # Instead, we should copy the code here to achive consistency of migrations
    # But for this case it looks fine and, what is more important, faster to import
    from ffun.domain.urls import url_to_uid

    cursor = conn.cursor()

    for feed in get_feeds(cursor):
        uid = url_to_uid(feed["url"])

        cursor.execute("UPDATE f_feeds SET uid = %(uid)s WHERE id = %(id)s", {"uid": uid, "id": feed["id"]})


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("UPDATE f_feeds SET uid = NULL")


steps = [step(apply_step, rollback_step)]
