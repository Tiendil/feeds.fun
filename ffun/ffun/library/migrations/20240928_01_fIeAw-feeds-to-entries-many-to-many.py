"""
feeds-to-entries-many-to-many
"""

from yoyo import step

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {'20240506_02_zQdSl-fix-unique-index-on-l-entries'}


# TODO: test on production data
# TODO: add index on created_at?

sql_create_feeds_to_entries_table = """
CREATE TABLE l_feeds_to_entries (
    feed_id UUID NOT NULL,
    entry_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    PRIMARY KEY (feed_id, entry_id),
    FOREIGN KEY (entry_id) REFERENCES l_entries (id)
)
"""

sql_fill_from_entries_table = """
INSERT INTO l_feeds_to_entries (feed_id, entry_id, created_at)
SELECT feed_id, id, created_at
FROM l_entries
"""


# rollback migration
sql_update_entries_from_m2m_table = """
UPDATE l_entries
SET feed_id = l_feeds_to_entries.feed_id
FROM l_feeds_to_entries
WHERE l_feeds_to_entries.entry_id = l_entries.id
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute(sql_create_feeds_to_entries_table)

    cursor.execute(sql_fill_from_entries_table)

    cursor.execute("ALTER TABLE l_entries DROP COLUMN feed_id")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("ALTER TABLE l_entries ADD COLUMN feed_id UUID DEFAULT NULL")

    cursor.execute(sql_update_entries_from_m2m_table)

    cursor.execute("ALTER TABLE l_entries ALTER COLUMN feed_id DROP DEFAULT")

    cursor.execute("DROP TABLE l_feeds_to_entries")


steps = [step(apply_step, rollback_step)]
