"""
published_at for feed-entry links
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {"20240928_01_fIeAw-feeds-to-entries-many-to-many"}


sql_add_published_at_column = """
ALTER TABLE l_feeds_to_entries
ADD COLUMN published_at TIMESTAMP WITH TIME ZONE NULL
"""

# We have no other source of truth for published_at value except l_entries.published_at
# so we can just copy values from l_entries.published_at to l_feeds_to_entries.published_at
# to have them as accurate as possible.
sql_fill_published_at_column = """
UPDATE l_feeds_to_entries AS f2e
SET published_at = e.published_at
FROM l_entries AS e
WHERE e.id = f2e.entry_id;
"""

sql_set_not_null_constraint = """
ALTER TABLE l_feeds_to_entries
ALTER COLUMN published_at SET NOT NULL;
"""

sql_drop_old_index = """
DROP INDEX IF EXISTS l_feeds_to_entries_feed_id_created_at_entity_id_idx
"""

# In case this index is too big, we may try reducing it to (feed_id, published_at DESC)
sql_create_new_index = """
CREATE INDEX l_feeds_to_entries_feed_id_published_at_created_at_entry_id_idx
ON l_feeds_to_entries(feed_id, published_at DESC, created_at DESC, entry_id)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute(sql_add_published_at_column)
    cursor.execute(sql_fill_published_at_column)
    cursor.execute(sql_set_not_null_constraint)
    cursor.execute(sql_drop_old_index)
    cursor.execute(sql_create_new_index)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP INDEX IF EXISTS l_feeds_to_entries_feed_id_published_at_created_at_entry_id_idx")
    cursor.execute("ALTER TABLE l_feeds_to_entries DROP COLUMN published_at")
    cursor.execute(
        """CREATE INDEX l_feeds_to_entries_feed_id_created_at_entity_id_idx
           ON l_feeds_to_entries(feed_id, created_at DESC, entry_id)"""
    )


steps = [step(apply_step, rollback_step)]
