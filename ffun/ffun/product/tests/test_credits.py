import datetime

from ffun.domain.datetime_intervals import LIFETIME_INTERVAL_START_MARKER
from ffun.entitlements.entities import EntitlementKindId
from ffun.product import credits
from ffun.product.entities import Credit, CreditDefinition, CreditUsageWindow, Resource


def test_credit_definitions() -> None:
    assert credits.CREDIT_DEFINITIONS == (
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
    assert credits.CREDIT_ENTITLEMENT_KINDS == (
        EntitlementKindId.day_tokens,
        EntitlementKindId.month_tokens,
        EntitlementKindId.lifetime_tokens,
    )


def test_credit_definitions__reservation_priority() -> None:
    assert tuple(definition.kind for definition in credits.CREDIT_DEFINITIONS) == (
        Credit.day,
        Credit.month,
        Credit.lifetime,
    )


class TestCreditUsageWindows:
    def test_success(self) -> None:
        at = datetime.datetime(2025, 2, 15, 12, 30, tzinfo=datetime.UTC)
        day_started_at = datetime.datetime(2025, 2, 15, tzinfo=datetime.UTC)
        month_started_at = datetime.datetime(2025, 2, 1, tzinfo=datetime.UTC)

        assert credits.credit_usage_windows(at) == (
            CreditUsageWindow(
                definition=credits.CREDIT_DEFINITIONS[0],
                resource_interval_started_at=day_started_at,
                period_started_at=day_started_at,
                period_ends_at=datetime.datetime(2025, 2, 16, tzinfo=datetime.UTC),
            ),
            CreditUsageWindow(
                definition=credits.CREDIT_DEFINITIONS[1],
                resource_interval_started_at=month_started_at,
                period_started_at=month_started_at,
                period_ends_at=datetime.datetime(2025, 3, 1, tzinfo=datetime.UTC),
            ),
            CreditUsageWindow(
                definition=credits.CREDIT_DEFINITIONS[2],
                resource_interval_started_at=LIFETIME_INTERVAL_START_MARKER,
                period_started_at=None,
                period_ends_at=None,
            ),
        )
