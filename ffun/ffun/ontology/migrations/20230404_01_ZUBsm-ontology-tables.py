from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()

sql_create_tags_table = """
CREATE TABLE o_tags (
    id BIGSERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW())
"""

sql_create_relations_table = """
CREATE TABLE o_relations (
    id BIGSERIAL PRIMARY KEY,
    entry_id UUID NOT NULL,
    tag_id BIGINT NOT NULL REFERENCES o_tags(id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW())
"""

sql_create_relations_entry_id_tag_id_index = """
CREATE UNIQUE INDEX idx_o_relations_entry_id_tag_id ON o_relations (entry_id, tag_id);
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_tags_table)
    cursor.execute(sql_create_relations_table)
    cursor.execute(sql_create_relations_entry_id_tag_id_index)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE o_tags, o_relations")


steps = [step(apply_step, rollback_step)]
