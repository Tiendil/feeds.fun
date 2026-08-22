"""
one-time purchases
"""

from typing import Any

from psycopg import Connection
from yoyo import step

__depends__: set[str] = set()


sql_create_purchases = """
-- Stores the latest accepted provider-neutral snapshot for each internal one-time purchase.
CREATE TABLE otp_purchases (
    id UUID NOT NULL PRIMARY KEY,
    state_transaction_id UUID NOT NULL,
    user_id UUID NOT NULL,
    benefit_id TEXT NOT NULL,
    status SMALLINT NOT NULL,
    provider_status TEXT NOT NULL,
    purchased_at TIMESTAMP WITH TIME ZONE NOT NULL,
    provider_updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
)
"""

sql_create_purchases_user_idx = """
-- Supports deterministic current-purchase listing for requested users.
CREATE INDEX otp_purchases_user_purchased_at_id_idx ON otp_purchases (
    user_id,
    purchased_at DESC,
    id
)
"""

sql_create_purchase_refs = """
-- Resolves an external provider purchase to its internal one-time-purchase projection.
CREATE TABLE otp_purchase_refs (
    provider_id TEXT NOT NULL,
    provider_account_id TEXT NOT NULL,
    provider_object_id TEXT NOT NULL,
    one_time_purchase_id UUID NOT NULL UNIQUE,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (provider_id, provider_account_id, provider_object_id)
)
"""


def apply_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute(sql_create_purchases)
    cursor.execute(sql_create_purchases_user_idx)
    cursor.execute(sql_create_purchase_refs)


def rollback_step(conn: Connection[dict[str, Any]]) -> None:
    cursor = conn.cursor()
    cursor.execute("DROP TABLE otp_purchase_refs")
    cursor.execute("DROP TABLE otp_purchases")


steps = [step(apply_step, rollback_step)]
