import datetime
from typing import cast

import pydantic
import pytest

from ffun.domain.domain import new_user_id
from ffun.subscriptions.entities import (
    ProviderCustomerId,
    ProviderId,
    ProviderMerchantId,
    ProviderSubscriptionId,
    SaveSubscriptionOutcome,
    SubscriptionStatusId,
)
from ffun.subscriptions.tests.make import make_subscription


class TestSubscriptionStatusId:
    def test_values_are_stable(self) -> None:
        assert [(status.name, status.value) for status in SubscriptionStatusId] == [
            ("pending", 1),
            ("trialing", 2),
            ("active", 3),
            ("past_due", 4),
            ("paused", 5),
            ("ended", 6),
        ]


class TestSaveSubscriptionOutcome:
    def test_values_are_stable(self) -> None:
        assert [(outcome.name, outcome.value) for outcome in SaveSubscriptionOutcome] == [
            ("created", 1),
            ("updated", 2),
            ("skipped", 3),
        ]


class TestSubscription:
    @pytest.mark.parametrize(
        "field_name",
        [
            "started_at",
            "renews_at",
            "ends_at",
            "provider_updated_at",
        ],
    )
    def test_init__timestamps_require_utc_offset(self, field_name: str) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)
        arguments: dict[str, object] = {field_name: now.replace(tzinfo=None)}

        with pytest.raises(pydantic.ValidationError, match=f"{field_name} must have a UTC offset"):
            make_subscription(**arguments)  # type: ignore[arg-type]

    def test_has_same_ownership_as__ignores_business_state(self) -> None:
        subscription = make_subscription()

        assert subscription.has_same_ownership_as(subscription.replace(status=SubscriptionStatusId.ended))

    @pytest.mark.parametrize(
        ("field_name", "different_value"),
        [
            ("provider_id", ProviderId("different-provider")),
            ("provider_merchant_id", ProviderMerchantId("different-merchant")),
            ("provider_subscription_id", ProviderSubscriptionId("different-subscription")),
            ("user_id", new_user_id()),
            ("provider_customer_id", ProviderCustomerId("different-customer")),
        ],
    )
    def test_has_same_ownership_as__different_ownership_field(
        self,
        field_name: str,
        different_value: object,
    ) -> None:
        subscription = make_subscription()

        assert not subscription.has_same_ownership_as(subscription.replace(**{field_name: different_value}))

    def test_has_same_business_state_as__ignores_only_provider_update_time(self) -> None:
        subscription = make_subscription()

        assert subscription.has_same_business_state_as(
            subscription.replace(provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=1))
        )
        assert not subscription.has_same_business_state_as(subscription.replace(status=SubscriptionStatusId.ended))

    def test_audit_state__serializes_complete_state_without_identity_and_ownership(self) -> None:
        subscription = make_subscription()

        state = subscription.audit_state()

        assert state == cast(
            dict[str, object],
            subscription.model_dump(
                mode="json",
                exclude={
                    "provider_id",
                    "provider_merchant_id",
                    "provider_subscription_id",
                    "user_id",
                    "provider_customer_id",
                },
            ),
        )
        assert "provider_updated_at" in state

    def test_business_event_attributes__serialize_complete_state_without_user(self) -> None:
        subscription = make_subscription()

        attributes = subscription.business_event_attributes()

        assert attributes == cast(
            dict[str, object],
            subscription.model_dump(mode="json", exclude={"user_id"}),
        )
