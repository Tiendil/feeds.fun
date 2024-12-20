"""
feeds-to-entries-many-to-many
"""

from typing import Any

from psycopg import Connection
from psycopg.rows import dict_row
from yoyo import step

__depends__ = {"20240928_02_lD7Bv-source-for-entries"}

sql_create_feeds_to_entries_table = """
CREATE TABLE l_feeds_to_entries (
    feed_id UUID NOT NULL,
    entry_id UUID NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    PRIMARY KEY (feed_id, entry_id),
    FOREIGN KEY (entry_id) REFERENCES l_entries (id)
)
"""


sql_create_orphaned_entries_table = """
CREATE TABLE l_orphaned_entries (
    entry_id UUID PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
)
"""


sql_fill_from_entries_table = """
INSERT INTO l_feeds_to_entries (feed_id, entry_id, created_at)
SELECT DISTINCT ON (source_id, external_id) feed_id, id, created_at
FROM l_entries
ORDER BY source_id, external_id ASC
"""


sql_fill_orphaned_entries = """
INSERT INTO l_orphaned_entries (entry_id)
SELECT id FROM l_entries
LEFT JOIN l_feeds_to_entries ON l_entries.id = l_feeds_to_entries.entry_id
WHERE l_feeds_to_entries.entry_id IS NULL
"""


sql_fill_duplicated_entries = """
WITH duplicates AS (
  SELECT id, source_id, external_id, l_entries.feed_id, l_entries.created_at
  FROM l_entries
  RIGHT JOIN l_orphaned_entries ON l_entries.id = l_orphaned_entries.entry_id
),

originals AS (
  SELECT id, source_id, external_id
  FROM l_entries
  LEFT JOIN l_feeds_to_entries ON l_entries.id = l_feeds_to_entries.entry_id
  WHERE l_feeds_to_entries.entry_id IS NOT NULL
)

INSERT INTO l_feeds_to_entries (feed_id, entry_id, created_at)
SELECT d.feed_id, o.id, d.created_at
FROM duplicates AS d
LEFT JOIN originals AS o ON d.source_id = o.source_id AND d.external_id = o.external_id
"""


sql_remove_duplicated_entries = """
DELETE FROM l_entries AS e
USING l_orphaned_entries AS o
WHERE e.id = o.entry_id
"""


# rollback migration
sql_update_entries_from_m2m_table = """
UPDATE l_entries
SET feed_id = x.feed_id
FROM (SELECT DISTINCT ON (entry_id) feed_id, entry_id FROM l_feeds_to_entries ORDER BY entry_id, created_at ASC) AS x
WHERE x.entry_id = l_entries.id
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor(row_factory=dict_row)

    cursor.execute(sql_create_feeds_to_entries_table)

    cursor.execute(sql_create_orphaned_entries_table)

    cursor.execute(sql_fill_from_entries_table)

    cursor.execute(sql_fill_orphaned_entries)

    cursor.execute("CREATE INDEX l_feeds_to_entries_entry_id_idx ON l_feeds_to_entries (entry_id)")

    cursor.execute(sql_fill_duplicated_entries)

    cursor.execute(sql_remove_duplicated_entries)

    # external_id goes first to optimize queries
    cursor.execute("CREATE UNIQUE INDEX l_entries_source_id_external_id_idx ON l_entries (external_id, source_id)")

    cursor.execute("ALTER TABLE l_entries DROP COLUMN feed_id")

    cursor.execute(
        """CREATE INDEX l_feeds_to_entries_feed_id_created_at_entity_id_idx
           ON l_feeds_to_entries(feed_id, created_at DESC, entry_id)"""
    )

    cursor.execute("CREATE INDEX l_entries_created_at_idx ON l_entries (created_at ASC)")


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("DROP INDEX l_entries_source_id_external_id_idx")

    cursor.execute("ALTER TABLE l_entries ADD COLUMN feed_id UUID DEFAULT NULL")

    cursor.execute(sql_update_entries_from_m2m_table)

    cursor.execute("ALTER TABLE l_entries ALTER COLUMN feed_id DROP DEFAULT")

    # after some tests there may be entries without a feed
    cursor.execute("DELETE FROM l_entries WHERE feed_id IS NULL")

    cursor.execute("ALTER TABLE l_entries ALTER COLUMN feed_id SET NOT NULL")

    cursor.execute("DROP TABLE l_orphaned_entries")
    cursor.execute("DROP TABLE l_feeds_to_entries")

    cursor.execute("CREATE UNIQUE INDEX l_entries_feed_id_external_id_key ON l_entries (feed_id, external_id)")
    cursor.execute("CREATE INDEX idx_l_entries_created_at_feed_id ON l_entries (created_at, feed_id)")


steps = [step(apply_step, rollback_step)]
