import datetime

from ffun.domain.datetime_intervals import (
    LIFETIME_INTERVAL_START_MARKER,
    day_interval_start,
    month_interval_start,
    next_month_start,
)
from ffun.entitlements.entities import EntitlementKindId
from ffun.product.entities import Credit, CreditDefinition, CreditUsageWindow, Resource

# Order defines credit spending priority and keeps dispatcher reservation options
# positionally aligned with their entitlement limits: day, then month, then lifetime.
CREDIT_DEFINITIONS: tuple[CreditDefinition, ...] = (
    CreditDefinition(
        kind=Credit.day,
        entitlement_kind=EntitlementKindId.day_tokens,
        resource_kind=Resource.day_token_usage,
    ),
    CreditDefinition(
        kind=Credit.month,
        entitlement_kind=EntitlementKindId.month_tokens,
        resource_kind=Resource.month_token_usage,
    ),
    CreditDefinition(
        kind=Credit.lifetime,
        entitlement_kind=EntitlementKindId.lifetime_tokens,
        resource_kind=Resource.lifetime_token_usage,
    ),
)

CREDIT_ENTITLEMENT_KINDS: tuple[EntitlementKindId, ...] = tuple(
    definition.entitlement_kind for definition in CREDIT_DEFINITIONS
)


def credit_usage_windows(at: datetime.datetime) -> tuple[CreditUsageWindow, ...]:
    day_started_at = day_interval_start(at)
    month_started_at = month_interval_start(at)
    definitions = {definition.kind: definition for definition in CREDIT_DEFINITIONS}

    return (
        CreditUsageWindow(
            definition=definitions[Credit.day],
            resource_interval_started_at=day_started_at,
            period_started_at=day_started_at,
            period_ends_at=day_started_at + datetime.timedelta(days=1),
        ),
        CreditUsageWindow(
            definition=definitions[Credit.month],
            resource_interval_started_at=month_started_at,
            period_started_at=month_started_at,
            period_ends_at=next_month_start(month_started_at),
        ),
        CreditUsageWindow(
            definition=definitions[Credit.lifetime],
            resource_interval_started_at=LIFETIME_INTERVAL_START_MARKER,
            period_started_at=None,
            period_ends_at=None,
        ),
    )
