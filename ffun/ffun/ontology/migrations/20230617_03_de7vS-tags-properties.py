"""
tags-properties
"""
from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20230617_02_L0MmA-tags-relationship-processor-tracking"}

sql_create_tags_properties_table = """
CREATE TABLE o_tags_properties (
    id BIGSERIAL PRIMARY KEY,
    tag_id BIGINT REFERENCES o_tags(id),
    type SMALLINT NOT NULL,
    value TEXT NOT NULL,
    processor_id BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW())
"""

sql_create_tags_properties_unique_index = """
CREATE UNIQUE INDEX idx_o_tags_properties_unique ON o_tags_properties(tag_id, type, processor_id)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_tags_properties_table)
    cursor.execute(sql_create_tags_properties_unique_index)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE o_tags_properties")


steps = [step(apply_step, rollback_step)]
