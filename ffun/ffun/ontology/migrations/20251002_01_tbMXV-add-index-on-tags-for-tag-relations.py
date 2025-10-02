"""
Add index on tags for tag relations
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = {"20240605_01_PC7sP-not-null-o-tags-properties-tag-id"}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("CREATE INDEX idx_o_relations_tag_id ON o_relations (tag_id);")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP INDEX idx_o_relations_tag_id;")


steps = [step(apply_step, rollback_step)]
