"""
benefit transactions
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()


sql_create_benefit_transactions = """
-- Immutable ledger of accepted purchased-state operations and their derived entitlement actions.
CREATE TABLE b_transactions (
    id UUID NOT NULL PRIMARY KEY,
    source_id SMALLINT NOT NULL,
    source_transaction_id UUID NOT NULL,
    entitlement_action SMALLINT NOT NULL,
    user_id UUID NOT NULL,
    benefit_id TEXT NOT NULL,
    subscription_id UUID,
    one_time_purchase_id UUID,
    effective_at TIMESTAMP WITH TIME ZONE NOT NULL,
    period_starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
    period_ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT b_transactions_source_identity_unique
        UNIQUE (source_id, source_transaction_id),
    CONSTRAINT b_transactions_exactly_one_target_check
        CHECK (num_nonnulls(subscription_id, one_time_purchase_id) = 1)
)
"""

sql_create_subscription_idx = """
-- Supports tracing the immutable transactions that produced one subscription projection.
CREATE INDEX b_transactions_subscription_id_idx ON b_transactions (subscription_id)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_benefit_transactions)
    cursor.execute(sql_create_subscription_idx)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE b_transactions")


steps = [step(apply_step, rollback_step)]
