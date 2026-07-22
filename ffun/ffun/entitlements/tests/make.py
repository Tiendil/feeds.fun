import datetime

from ffun.domain.domain import new_user_id
from ffun.domain.entities import UserId
from ffun.entitlements.entities import (
    EffectiveEntitlementInterval,
    EntitlementKindId,
    EntitlementSourceId,
    EntitlementTransactionId,
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
    source: EntitlementSourceId = EntitlementSourceId("test"),
    transaction_id: EntitlementTransactionId = EntitlementTransactionId("test-transaction"),
    kind_id: EntitlementKindId = EntitlementKindId.day_tokens,
    value: int = 10,
    starts_at: datetime.datetime | None = None,
    expires_at: datetime.datetime | None = None,
    revoked_at: datetime.datetime | None = None,
) -> SourceEntitlement:
    now = datetime.datetime.now(tz=datetime.UTC)
    return SourceEntitlement(
        source=source,
        transaction_id=transaction_id,
        user_id=user_id or new_user_id(),
        kind_id=kind_id,
        value=value,
        starts_at=starts_at or now - datetime.timedelta(days=1),
        expires_at=expires_at or now + datetime.timedelta(days=1),
        revoked_at=revoked_at,
    )
