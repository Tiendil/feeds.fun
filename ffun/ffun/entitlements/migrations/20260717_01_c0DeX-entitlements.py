"""
entitlements
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()


sql_create_source_entitlements = """
-- Stores the latest entitlement state supplied by every source.
CREATE TABLE en_source_entitlements (
    source_id TEXT NOT NULL,
    user_id UUID NOT NULL,
    kind_id SMALLINT NOT NULL,
    granted BOOLEAN NOT NULL,
    value BIGINT,
    starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, kind_id, source_id)
)
"""

sql_create_entitlements = """
-- Materialized effective entitlement intervals derived from the source entitlement table.
CREATE TABLE en_entitlements (
    user_id UUID NOT NULL,
    kind_id SMALLINT NOT NULL,
    value BIGINT NOT NULL,
    starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, kind_id, starts_at)
)
"""

sql_create_entitlements_expires_at_idx = """
-- Supports removal of expired effective intervals.
CREATE INDEX en_entitlements_expires_at_idx ON en_entitlements (expires_at)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_source_entitlements)
    cursor.execute(sql_create_entitlements)
    cursor.execute(sql_create_entitlements_expires_at_idx)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE en_entitlements")
    cursor.execute("DROP TABLE en_source_entitlements")


steps = [step(apply_step, rollback_step)]
