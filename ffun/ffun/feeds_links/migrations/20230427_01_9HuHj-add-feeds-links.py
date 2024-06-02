"""
add-feeds-links
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()

sql_create_feeds_links_table = """
CREATE TABLE fl_links (
    id UUID PRIMARY KEY,
    feed_id UUID NOT NULL,
    user_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW())
"""

sql_create_unique_index = """
CREATE UNIQUE INDEX idx_fl_links_user_id_feed_id ON fl_links (user_id, feed_id)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_feeds_links_table)
    cursor.execute(sql_create_unique_index)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE fl_links")


steps = [step(apply_step, rollback_step)]
