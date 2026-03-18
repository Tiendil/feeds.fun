"""
Ingested time for entries
"""
from typing import Any

from psycopg import Connection
from yoyo import step

__depends__ = {'20260314_01_epp7e-published-at-for-feed-entry-links'}


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("ALTER TABLE l_feeds_to_entries RENAME COLUMN published_at TO ingested_at")
    cursor.execute("UPDATE l_feeds_to_entries SET ingested_at = created_at")
    cursor.execute("ALTER TABLE l_feeds_to_entries ADD COLUMN entry_created_at TIMESTAMP WITH TIME ZONE NULL")
    cursor.execute("""
    UPDATE l_feeds_to_entries AS f2e
    SET entry_created_at = e.created_at
    FROM l_entries AS e
    WHERE e.id = f2e.entry_id
    """)
    cursor.execute("ALTER TABLE l_feeds_to_entries ALTER COLUMN entry_created_at SET NOT NULL")
    cursor.execute("DROP INDEX IF EXISTS l_feeds_to_entries_feed_id_published_at_created_at_entry_id_idx")
    cursor.execute("""
    CREATE INDEX l_feeds_to_entries_feed_id_created_at_entry_id_idx
    ON l_feeds_to_entries(feed_id, created_at DESC, entry_id DESC)
    """)
    cursor.execute("""
    CREATE INDEX l_feeds_to_entries_feed_id_entry_created_at_entry_id_idx
    ON l_feeds_to_entries(feed_id, entry_created_at DESC, entry_id DESC)
    """)
    cursor.execute("""
    CREATE INDEX l_feeds_to_entries_feed_id_ingested_at_idx
    ON l_feeds_to_entries(feed_id, ingested_at DESC)
    """)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()

    cursor.execute("DROP INDEX IF EXISTS l_feeds_to_entries_feed_id_ingested_at_idx")
    cursor.execute("DROP INDEX IF EXISTS l_feeds_to_entries_feed_id_created_at_entry_id_idx")
    cursor.execute("DROP INDEX IF EXISTS l_feeds_to_entries_feed_id_entry_created_at_entry_id_idx")
    cursor.execute("ALTER TABLE l_feeds_to_entries DROP COLUMN entry_created_at")
    cursor.execute("ALTER TABLE l_feeds_to_entries RENAME COLUMN ingested_at TO published_at")
    cursor.execute("""
    CREATE INDEX l_feeds_to_entries_feed_id_published_at_created_at_entry_id_idx
    ON l_feeds_to_entries(feed_id, published_at DESC, created_at DESC, entry_id)
    """)


steps = [step(apply_step, rollback_step)]
