"""
tags-relationship-processor-tracking
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20230617_01_XDdNG-rename-tags-names-to-uid"}

sql_create_relatons_processors_table = """
CREATE TABLE o_relations_processors (
    relation_id BIGINT REFERENCES o_relations(id),
    processor_id BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (relation_id, processor_id)
)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_relatons_processors_table)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE o_relations_processors")


steps = [step(apply_step, rollback_step)]
