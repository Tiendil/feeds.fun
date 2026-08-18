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
    renews_at TIMESTAMP WITH TIME ZONE DEFAULT NULL,
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


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_subscriptions)
    cursor.execute(sql_create_subscriptions_user_idx)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE sb_subscriptions")


steps = [step(apply_step, rollback_step)]
