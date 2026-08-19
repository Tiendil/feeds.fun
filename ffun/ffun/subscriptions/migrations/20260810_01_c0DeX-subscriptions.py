"""
subscriptions
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()


sql_create_subscriptions = """
-- Stores the latest accepted provider-neutral snapshot for each internal subscription.
CREATE TABLE sb_subscriptions (
    id UUID NOT NULL PRIMARY KEY,
    state_transaction_id UUID NOT NULL,
    user_id UUID NOT NULL,
    benefit_id TEXT NOT NULL,
    status SMALLINT NOT NULL,
    provider_status TEXT NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    period_starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
    period_ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
    expected_renewal_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    ends_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
    provider_updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

sql_create_subscriptions_user_idx = """
-- Supports deterministic current-subscription listing for requested users.
CREATE INDEX sb_subscriptions_user_started_at_id_idx ON sb_subscriptions (
    user_id,
    started_at DESC,
    id
)
"""

sql_create_subscription_refs = """
-- Resolves an external provider subscription to its internal subscription projection.
CREATE TABLE sb_subscription_refs (
    provider_id TEXT NOT NULL,
    provider_account_id TEXT NOT NULL,
    provider_subscription_id TEXT NOT NULL,
    subscription_id UUID NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provider_id, provider_account_id, provider_subscription_id)
)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_subscriptions)
    cursor.execute(sql_create_subscriptions_user_idx)
    cursor.execute(sql_create_subscription_refs)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE sb_subscription_refs")
    cursor.execute("DROP TABLE sb_subscriptions")


steps = [step(apply_step, rollback_step)]
