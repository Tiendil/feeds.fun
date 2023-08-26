"""
rename-tags-names-to-uid
"""
from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20230404_01_ZUBsm-ontology-tables"}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE o_tags RENAME COLUMN name TO uid;")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE o_tags RENAME COLUMN uid TO name;")


steps = [step(apply_step, rollback_step)]
