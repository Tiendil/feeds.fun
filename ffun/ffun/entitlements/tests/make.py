import datetime
import uuid

from ffun.domain.domain import new_user_id
from ffun.domain.entities import BenefitTransactionId, SubscriptionId, UserId
from ffun.entitlements.entities import (
    EffectiveEntitlementInterval,
    EntitlementKindId,
    EntitlementSourceId,
    SourceEntitlement,
)


def make_effective_entitlement_interval(
    *,
    user_id: UserId | None = None,
    kind_id: EntitlementKindId = EntitlementKindId.day_tokens,
    value: int = 10,
    starts_at: datetime.datetime | None = None,
    expires_at: datetime.datetime | None = None,
) -> EffectiveEntitlementInterval:
    now = datetime.datetime.now(tz=datetime.UTC)
    return EffectiveEntitlementInterval(
        user_id=user_id or new_user_id(),
        kind_id=kind_id,
        value=value,
        starts_at=starts_at or now - datetime.timedelta(days=1),
        expires_at=expires_at or now + datetime.timedelta(days=1),
    )


def make_source_entitlement(  # noqa: CFQ002
    *,
    user_id: UserId | None = None,
    source_id: EntitlementSourceId = EntitlementSourceId("test"),
    grant_transaction_id: BenefitTransactionId | None = None,
    subscription_id: SubscriptionId | None = None,
    kind_id: EntitlementKindId = EntitlementKindId.day_tokens,
    value: int = 10,
    starts_at: datetime.datetime | None = None,
    expires_at: datetime.datetime | None = None,
    revoked_at: datetime.datetime | None = None,
    revoked_by_transaction_id: BenefitTransactionId | None = None,
) -> SourceEntitlement:
    now = datetime.datetime.now(tz=datetime.UTC)
    return SourceEntitlement(
        source_id=source_id,
        grant_transaction_id=grant_transaction_id or BenefitTransactionId(uuid.uuid4()),
        user_id=user_id or new_user_id(),
        subscription_id=subscription_id,
        kind_id=kind_id,
        value=value,
        starts_at=starts_at or now - datetime.timedelta(days=1),
        expires_at=expires_at or now + datetime.timedelta(days=1),
        revoked_at=revoked_at,
        revoked_by_transaction_id=(
            revoked_by_transaction_id or BenefitTransactionId(uuid.uuid4()) if revoked_at is not None else None
        ),
    )
