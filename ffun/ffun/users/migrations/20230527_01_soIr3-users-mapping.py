"""
users-mapping
"""

from yoyo import step

__depends__ = {}


sql_create_user_mapping_table = """
CREATE TABLE u_mapping (
    external_id TEXT NOT NULL,
    internal_id UUID PRIMARY KEY,
    service_id INTEGER NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
"""

sql_create_service_index = '''
CREATE UNIQUE INDEX idx_u_mapping_service_id_external_id ON u_mapping (service_id, external_id);
'''


def apply_step(conn):
    cursor = conn.cursor()
    cursor.execute(sql_create_user_mapping_table)
    cursor.execute(sql_create_service_index)


def rollback_step(conn):
    cursor = conn.cursor()
    cursor.execute("DROP TABLE u_mapping")


steps = [step(apply_step, rollback_step)]
