"""
entitlements
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()


sql_create_source_entitlements = """
-- Stores entitlement grants caused by benefit transactions.
CREATE TABLE en_source_entitlements (
    grant_transaction_id UUID NOT NULL,
    user_id UUID NOT NULL,
    subscription_id UUID DEFAULT NULL,
    one_time_purchase_id UUID DEFAULT NULL,
    kind_id SMALLINT NOT NULL,
    value BIGINT NOT NULL,
    starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    revoked_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    revoked_by_transaction_id UUID DEFAULT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT en_source_entitlements_at_most_one_owner_check
        CHECK (num_nonnulls(subscription_id, one_time_purchase_id) <= 1),
    PRIMARY KEY (grant_transaction_id, kind_id)
)
"""

sql_create_source_entitlements_user_kind_idx = """
CREATE INDEX en_source_entitlements_user_id_kind_id_idx
ON en_source_entitlements (user_id, kind_id)
"""

sql_create_source_entitlements_subscription_idx = """
CREATE INDEX en_source_entitlements_subscription_id_idx
ON en_source_entitlements (subscription_id)
WHERE subscription_id IS NOT NULL
"""

sql_create_source_entitlements_one_time_purchase_idx = """
CREATE INDEX en_source_entitlements_one_time_purchase_id_idx
ON en_source_entitlements (one_time_purchase_id)
WHERE one_time_purchase_id IS NOT NULL
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
    cursor.execute(sql_create_source_entitlements_user_kind_idx)
    cursor.execute(sql_create_source_entitlements_subscription_idx)
    cursor.execute(sql_create_source_entitlements_one_time_purchase_idx)
    cursor.execute(sql_create_entitlements)
    cursor.execute(sql_create_entitlements_expires_at_idx)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE en_entitlements")
    cursor.execute("DROP TABLE en_source_entitlements")


steps = [step(apply_step, rollback_step)]
