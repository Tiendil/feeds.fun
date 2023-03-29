
from yoyo import step

__depends__ = {}


sql_create_feeds_table = '''
CREATE TABLE f_feeds (
    id UUID PRIMARY KEY,
    url TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW())
'''


def apply_step(conn):
    cursor = conn.cursor()
    cursor.execute(sql_create_feeds_table)


def rollback_step(conn):
    cursor = conn.cursor()
    cursor.execute(f"DROP TABLE f_feeds")


steps = [step(apply_step, rollback_step)]
