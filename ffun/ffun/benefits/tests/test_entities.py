import datetime
from typing import cast

import pydantic
import pytest

from ffun.benefits.entities import (
    BenefitEntitlementAction,
    BenefitPackage,
    BenefitTransaction,
    InternalSubscriptionTarget,
    NewSubscriptionTarget,
)
from ffun.benefits.tests.make import (
    make_benefit_package,
    make_benefit_transaction,
    make_external_subscription_target,
    make_transaction_command,
)
from ffun.core.entities import NonEmptyString
from ffun.domain.entities import BenefitId
from ffun.entitlements.entities import EntitlementGuarantee, EntitlementKindId
from ffun.subscriptions.domain import new_subscription_id
from ffun.subscriptions.tests.make import make_provider_subscription_reference


class TestBenefitEntitlementAction:
    def test_values_are_stable(self) -> None:
        assert [(action.name, action.value) for action in BenefitEntitlementAction] == [
            ("grant", 1),
            ("revoke", 2),
        ]


class TestBenefitPackage:
    def test_entitlements__defaults_to_empty(self) -> None:
        package = BenefitPackage(
            id=BenefitId("empty"),
            title=NonEmptyString("Empty"),
            description="No guarantees",
        )

        assert package.entitlements == ()

    def test_entitlement_kinds_must_be_unique__accepts_distinct_kinds(self) -> None:
        package = make_benefit_package(
            entitlements=(
                EntitlementGuarantee(kind_id=EntitlementKindId.day_tokens, value=10),
                EntitlementGuarantee(kind_id=EntitlementKindId.month_tokens, value=20),
            )
        )

        assert len(package.entitlements) == 2

    def test_entitlement_kinds_must_be_unique__rejects_duplicate_kind(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="entitlement kinds must be unique"):
            make_benefit_package(
                entitlements=(
                    EntitlementGuarantee(kind_id=EntitlementKindId.day_tokens, value=10),
                    EntitlementGuarantee(kind_id=EntitlementKindId.day_tokens, value=20),
                )
            )


class TestInternalSubscriptionTarget:
    def test_provider_reference__is_missing(self) -> None:
        target = InternalSubscriptionTarget(subscription_id=new_subscription_id())

        assert target.provider_reference is None


class TestExternalSubscriptionTarget:
    def test_provider_reference__contains_external_identity(self) -> None:
        reference = make_provider_subscription_reference()
        target = make_external_subscription_target(reference)

        assert target.provider_reference == reference

    def test_identity__returns_ordered_external_identity(self) -> None:
        target = make_external_subscription_target()

        assert target.identity == (
            target.provider_id,
            target.provider_account_id,
            target.provider_subscription_id,
        )


class TestNewSubscriptionTarget:
    def test_provider_reference__is_missing(self) -> None:
        assert NewSubscriptionTarget().provider_reference is None


class TestBenefitTransactionCommand:
    def test_source_identity__returns_source_tuple(self) -> None:
        command = make_transaction_command()

        assert command.source_identity == (command.source_id, command.source_transaction_id)

    def test_effective_at_must_have_timezone__rejects_naive_timestamp(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="effective timestamp must have a UTC offset"):
            make_transaction_command(effective_at=datetime.datetime.now())


class TestBenefitTransaction:
    def test_source_identity__returns_source_tuple(self) -> None:
        transaction = make_benefit_transaction()

        assert transaction.source_identity == (transaction.source_id, transaction.source_transaction_id)

    @pytest.mark.parametrize("field_name", ["effective_at", "period_starts_at", "period_ends_at"])
    def test_timestamp_must_have_timezone__rejects_naive_timestamp(self, field_name: str) -> None:
        transaction = make_benefit_transaction()
        data = cast(dict[str, object], transaction.model_dump())
        timestamp = cast(datetime.datetime, data[field_name])
        data[field_name] = timestamp.replace(tzinfo=None)

        with pytest.raises(pydantic.ValidationError, match=rf"timestamp {field_name} must have a UTC offset"):
            BenefitTransaction.model_validate(data)

    def test_validate_period_order__start_must_be_before_end(self) -> None:
        transaction = make_benefit_transaction()
        data = cast(dict[str, object], transaction.model_dump())
        data["period_starts_at"] = data["period_ends_at"]

        with pytest.raises(pydantic.ValidationError, match="period start must be earlier than period end"):
            BenefitTransaction.model_validate(data)
