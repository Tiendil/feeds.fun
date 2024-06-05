"""
not-null-o_tags_properties-tag_id
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20230617_03_de7vS-tags-properties"}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("ALTER TABLE o_tags_properties ALTER COLUMN tag_id SET NOT NULL")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("ALTER TABLE o_tags_properties ALTER COLUMN tag_id DROP NOT NULL")


steps = [step(apply_step, rollback_step)]
