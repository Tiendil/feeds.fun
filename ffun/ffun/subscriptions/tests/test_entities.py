import datetime
from typing import cast

import pydantic
import pytest

from ffun.domain.entities import BenefitId, BenefitTransactionId
from ffun.subscriptions.entities import (
    SaveSubscriptionOutcome,
    SubscriptionSnapshot,
    SubscriptionStatusId,
)
from ffun.subscriptions.operations import new_subscription_id
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


class TestSubscriptionSnapshot:
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

    def test_has_same_business_state_as__ignores_only_provider_update_time(self) -> None:
        subscription = make_subscription()

        assert subscription.has_same_business_state_as(
            subscription.replace(provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=1))
        )
        assert not subscription.has_same_business_state_as(subscription.replace(status=SubscriptionStatusId.ended))

    def test_business_state__contains_snapshot_except_provider_update_time(self) -> None:
        subscription = make_subscription()

        state = subscription.business_state()

        assert state == cast(
            dict[str, object],
            subscription.model_dump(
                include=set(SubscriptionSnapshot.model_fields) - {"provider_updated_at"},
            ),
        )

    def test_audit_state__serializes_complete_snapshot_without_user(self) -> None:
        subscription = make_subscription()
        snapshot = SubscriptionSnapshot.model_validate(
            cast(dict[str, object], subscription.model_dump(exclude={"id", "state_transaction_id"}))
        )

        state = snapshot.audit_state()

        assert state == cast(
            dict[str, object],
            snapshot.model_dump(mode="json", exclude={"user_id"}),
        )
        assert "provider_updated_at" in state

    def test_with_identity__creates_complete_subscription(self) -> None:
        subscription = make_subscription()
        snapshot = SubscriptionSnapshot.model_validate(
            cast(dict[str, object], subscription.model_dump(exclude={"id", "state_transaction_id"}))
        )
        subscription_id = new_subscription_id()
        state_transaction_id = BenefitTransactionId(subscription.state_transaction_id)

        result = snapshot.with_identity(
            subscription_id=subscription_id,
            state_transaction_id=state_transaction_id,
        )

        assert result == subscription.replace(
            id=subscription_id,
            state_transaction_id=state_transaction_id,
        )


class TestSubscription:
    def test_audit_state__serializes_complete_snapshot_without_internal_identity_or_user(self) -> None:
        subscription = make_subscription()

        state = subscription.audit_state()

        assert state == cast(
            dict[str, object],
            subscription.model_dump(
                mode="json",
                exclude={"id", "state_transaction_id", "user_id"},
            ),
        )
        assert state["benefit_id"] == BenefitId("test-benefit")

    def test_business_event_attributes__serialize_complete_state_without_user(self) -> None:
        subscription = make_subscription()

        attributes = subscription.business_event_attributes()

        expected = cast(
            dict[str, object],
            subscription.model_dump(mode="json", exclude={"id", "user_id"}),
        )
        expected["subscription_id"] = str(subscription.id)

        assert attributes == expected
        assert "state_transaction_id" in attributes
