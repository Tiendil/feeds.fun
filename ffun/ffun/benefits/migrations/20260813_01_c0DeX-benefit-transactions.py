"""
benefit transactions
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()


sql_create_benefit_transactions = """
-- Immutable ledger of accepted operations that may change subscriptions and entitlement grants.
CREATE TABLE b_transactions (
    id UUID NOT NULL PRIMARY KEY,
    source_id SMALLINT NOT NULL,
    source_transaction_id UUID NOT NULL,
    kind SMALLINT NOT NULL,
    user_id UUID NOT NULL,
    benefit_id TEXT NOT NULL,
    subscription_id UUID DEFAULT NULL,
    effective_at TIMESTAMP WITH TIME ZONE NOT NULL,
    period_starts_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    period_ends_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    revokes_transaction_id UUID DEFAULT NULL REFERENCES b_transactions (id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT b_transactions_source_identity_unique
        UNIQUE (source_id, source_transaction_id)
)
"""

sql_create_subscription_idx = """
-- Supports tracing the immutable transactions that produced one subscription projection.
CREATE INDEX b_transactions_subscription_id_idx ON b_transactions (subscription_id)
WHERE subscription_id IS NOT NULL
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_benefit_transactions)
    cursor.execute(sql_create_subscription_idx)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE b_transactions")


steps = [step(apply_step, rollback_step)]
