"""
entries_table
"""

from yoyo import step

__depends__ = {}


sql_create_entries_table = '''
CREATE TABLE l_entries (
    id UUID PRIMARY KEY,
    feed_id UUID NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    external_id TEXT NOT NULL UNIQUE,
    external_url TEXT NOT NULL,
    external_tags TEXT[] NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    cataloged_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
)
'''


sql_create_feeds_index = '''
CREATE INDEX idx_l_entries_feed_id ON l_entries (feed_id);
'''


def apply_step(conn):
    cursor = conn.cursor()
    cursor.execute(sql_create_entries_table)
    cursor.execute(sql_create_feeds_index)


def rollback_step(conn):
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE l_entries")


steps = [step(apply_step, rollback_step)]
