
from yoyo import step

__depends__ = {}


sql_create_feeds_table = '''
CREATE TABLE f_feeds (
    id UUID PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    loaded_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW())
'''

sql_create_loaded_at_index = '''
CREATE INDEX idx_f_feeds_loaded_at ON f_feeds (loaded_at);
'''


def apply_step(conn):
    cursor = conn.cursor()
    cursor.execute(sql_create_feeds_table)
    cursor.execute(sql_create_loaded_at_index)


def rollback_step(conn):
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE f_feeds")


steps = [step(apply_step, rollback_step)]
