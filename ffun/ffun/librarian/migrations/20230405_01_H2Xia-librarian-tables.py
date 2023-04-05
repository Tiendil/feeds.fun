"""
librarian-tables
"""

from yoyo import step

__depends__ = {}

sql_create_entry_process_info_table = '''
CREATE TABLE ln_entry_process_info (
    id BIGSERIAL PRIMARY KEY,
    entry_id UUID NOT NULL,
    processor_id INTEGER NOT NULL,
    cataloged_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE NULL DEFAULT NULL)
'''


sql_create_entry_process_info_entry_id_processor_id_index = '''
CREATE UNIQUE INDEX idx_ln_entry_process_info_entry_id_processor_id ON ln_entry_process_info (entry_id, processor_id);
'''


sql_create_entry_process_info_processor_id_processed_at_index = '''
CREATE INDEX idx_ln_entry_process_info_processor_id_processed_at ON ln_entry_process_info (processor_id, processed_at);
'''


sql_create_entry_process_info_processor_id_cataloged_at_index = '''
CREATE INDEX idx_ln_entry_process_info_processor_id_cataloged_at ON ln_entry_process_info (processor_id, cataloged_at);
'''


def apply_step(conn):
    cursor = conn.cursor()
    cursor.execute(sql_create_entry_process_info_table)
    cursor.execute(sql_create_entry_process_info_entry_id_processor_id_index)
    cursor.execute(sql_create_entry_process_info_processor_id_processed_at_index)
    cursor.execute(sql_create_entry_process_info_processor_id_cataloged_at_index)


def rollback_step(conn):
    cursor = conn.cursor()
    cursor.execute('DROP TABLE ln_entry_process_info')


steps = [step(apply_step, rollback_step)]
