"""
column-for-feed-unique-id
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20230426_01_IiF5m-add-title-and-description"}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    sql = "ALTER TABLE f_feeds ADD COLUMN uid TEXT DEFAULT NULL"

    cursor.execute(sql)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    sql = "ALTER TABLE f_feeds DROP COLUMN uid"

    cursor.execute(sql)


steps = [step(apply_step, rollback_step)]
