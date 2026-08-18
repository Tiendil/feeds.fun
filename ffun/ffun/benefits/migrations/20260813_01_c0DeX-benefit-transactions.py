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
    starts_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    expires_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    reverses_transaction_id UUID DEFAULT NULL REFERENCES b_transactions (id),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT b_transactions_source_identity_unique
        UNIQUE (source_id, source_transaction_id)
)
"""

sql_create_subscription_refs = """
-- Resolves an external provider subscription to its internal subscription projection.
CREATE TABLE b_subscription_refs (
    provider_id TEXT NOT NULL,
    provider_account_id TEXT NOT NULL,
    provider_subscription_id TEXT NOT NULL,
    subscription_id UUID NOT NULL,
    PRIMARY KEY (provider_id, provider_account_id, provider_subscription_id)
)
"""

sql_create_subscription_refs_subscription_idx = """
CREATE INDEX b_subscription_refs_subscription_id_idx ON b_subscription_refs (subscription_id)
"""

sql_create_subscription_idx = """
-- Supports tracing the immutable transactions that produced one subscription projection.
CREATE INDEX b_transactions_subscription_id_idx ON b_transactions (subscription_id)
WHERE subscription_id IS NOT NULL
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_benefit_transactions)
    cursor.execute(sql_create_subscription_refs)
    cursor.execute(sql_create_subscription_refs_subscription_idx)
    cursor.execute(sql_create_subscription_idx)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE b_subscription_refs")
    cursor.execute("DROP TABLE b_transactions")


steps = [step(apply_step, rollback_step)]
