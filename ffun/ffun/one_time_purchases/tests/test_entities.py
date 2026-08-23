import datetime
from typing import cast

import pydantic
import pytest

from ffun.domain.datetime_intervals import LIFETIME_INTERVAL_END_MARKER
from ffun.domain.entities import BenefitId, BenefitTransactionId
from ffun.one_time_purchases.entities import PurchaseSnapshot, PurchaseStatus
from ffun.one_time_purchases.operations import new_purchase_id
from ffun.one_time_purchases.tests.make import make_purchase


class TestPurchaseStatus:
    def test_values_are_stable(self) -> None:
        assert [(status.name, status.value) for status in PurchaseStatus] == [
            ("pending", 1),
            ("completed", 2),
            ("refunded", 3),
            ("reversed", 4),
            ("disputed", 5),
        ]

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (PurchaseStatus.pending, False),
            (PurchaseStatus.completed, True),
            (PurchaseStatus.refunded, False),
            (PurchaseStatus.reversed, False),
            (PurchaseStatus.disputed, False),
        ],
    )
    def test_grants_benefits(self, status: PurchaseStatus, expected: bool) -> None:
        assert status.grants_benefits == expected


class TestPurchaseSnapshot:
    @pytest.mark.parametrize("field_name", ["purchased_at", "provider_updated_at"])
    def test_init__timestamps_require_utc_offset(self, field_name: str) -> None:
        arguments: dict[str, object] = {field_name: datetime.datetime.now(tz=datetime.UTC).replace(tzinfo=None)}

        with pytest.raises(pydantic.ValidationError, match=f"{field_name} must have a UTC offset"):
            make_purchase(**arguments)  # type: ignore[arg-type]

    def test_period_starts_at__uses_purchase_time(self) -> None:
        purchase = make_purchase()

        assert purchase.period_starts_at == purchase.purchased_at

    def test_period_ends_at__uses_lifetime_marker(self) -> None:
        assert make_purchase().period_ends_at == LIFETIME_INTERVAL_END_MARKER

    def test_init__purchase_time_must_precede_lifetime_end(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="earlier than the lifetime interval end"):
            make_purchase(purchased_at=LIFETIME_INTERVAL_END_MARKER)

    def test_has_same_business_state_as__ignores_only_provider_update_time(self) -> None:
        purchase = make_purchase()

        assert purchase.has_same_business_state_as(
            purchase.replace(provider_updated_at=purchase.provider_updated_at + datetime.timedelta(seconds=1))
        )
        assert not purchase.has_same_business_state_as(purchase.replace(status=PurchaseStatus.refunded))

    def test_business_state__contains_snapshot_except_provider_update_time(self) -> None:
        purchase = make_purchase()

        state = purchase.business_state()

        assert state == cast(
            dict[str, object],
            purchase.model_dump(
                include=set(PurchaseSnapshot.model_fields) - {"provider_updated_at"},
            ),
        )

    def test_audit_state__serializes_complete_snapshot_without_user(self) -> None:
        purchase = make_purchase()
        snapshot = PurchaseSnapshot.model_validate(
            cast(dict[str, object], purchase.model_dump(exclude={"id", "state_transaction_id"}))
        )

        state = snapshot.audit_state()

        assert state == cast(
            dict[str, object],
            snapshot.model_dump(mode="json", exclude={"user_id"}),
        )
        assert "provider_updated_at" in state

    def test_with_identity__creates_complete_purchase(self) -> None:
        purchase = make_purchase()
        snapshot = PurchaseSnapshot.model_validate(
            cast(dict[str, object], purchase.model_dump(exclude={"id", "state_transaction_id"}))
        )
        one_time_purchase_id = new_purchase_id()
        state_transaction_id = BenefitTransactionId(purchase.state_transaction_id)

        result = snapshot.with_identity(
            one_time_purchase_id=one_time_purchase_id,
            state_transaction_id=state_transaction_id,
        )

        assert result == purchase.replace(
            id=one_time_purchase_id,
            state_transaction_id=state_transaction_id,
        )


class TestPurchase:
    def test_audit_state__serializes_complete_snapshot_without_internal_identity_or_user(self) -> None:
        purchase = make_purchase()

        state = purchase.audit_state()

        assert state == cast(
            dict[str, object],
            purchase.model_dump(
                mode="json",
                exclude={"id", "state_transaction_id", "user_id"},
            ),
        )
        assert state["benefit_id"] == BenefitId("test-benefit")

    def test_business_event_attributes__serialize_complete_state_without_user(self) -> None:
        purchase = make_purchase()

        attributes = purchase.business_event_attributes()

        expected = cast(
            dict[str, object],
            purchase.model_dump(mode="json", exclude={"id", "user_id"}),
        )
        expected["one_time_purchase_id"] = str(purchase.id)

        assert attributes == expected
        assert "state_transaction_id" in attributes
