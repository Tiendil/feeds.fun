from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20240928_01_OEKOr-source-table"}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE f_feeds ADD COLUMN site_url TEXT DEFAULT NULL")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE f_feeds DROP COLUMN site_url")


steps = [step(apply_step, rollback_step)]
