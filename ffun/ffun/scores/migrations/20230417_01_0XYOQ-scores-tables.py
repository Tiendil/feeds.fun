"""
scores-tables
"""

from yoyo import step

__depends__ = {}

steps = [
    step("")
]


sql_create_rules_table = '''
CREATE TABLE s_rules (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    tags BIGINT[] NOT NULL,
    key TEXT NOT NULL,
    score INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
)
'''

sql_users_key_index = '''
CREATE UNIQUE INDEX idx_s_rules_user_id ON s_rules (user_id, key);
'''


def apply_step(conn):
    cursor = conn.cursor()
    cursor.execute(sql_create_rules_table)
    cursor.execute(sql_users_key_index)


def rollback_step(conn):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE s_rules")


steps = [step(apply_step, rollback_step)]
