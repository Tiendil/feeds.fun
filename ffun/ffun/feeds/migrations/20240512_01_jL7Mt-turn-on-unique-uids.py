"""
turn-on-unique-uids
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20240504_02_gEapd-fill-uids-for-feeds"}


unique_index = "idx_f_feeds_uid"


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("ALTER TABLE f_feeds ALTER COLUMN uid SET NOT NULL")
    cursor.execute(f"ALTER TABLE f_feeds ADD CONSTRAINT {unique_index} UNIQUE (uid)")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(f"ALTER TABLE f_feeds DROP CONSTRAINT {unique_index}")
    cursor.execute("ALTER TABLE f_feeds ALTER COLUMN uid DROP NOT NULL")


steps = [step(apply_step, rollback_step)]
