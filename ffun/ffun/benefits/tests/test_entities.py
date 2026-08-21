import datetime
from typing import cast

import pydantic
import pytest

from ffun.benefits import errors
from ffun.benefits.entities import (
    BenefitEntitlementAction,
    BenefitPackageTemplate,
    BenefitParameterDefinition,
    BenefitParameterId,
    BenefitTransaction,
    InternalSubscriptionTarget,
    NewSubscriptionTarget,
    ParameterConstant,
    ParameterReference,
)
from ffun.benefits.tests.make import (
    make_benefit_package,
    make_benefit_transaction,
    make_external_subscription_target,
    make_transaction_command,
)
from ffun.core.entities import NonEmptyString
from ffun.domain.entities import BenefitId
from ffun.entitlements.entities import MAX_ENTITLEMENT_VALUE, EntitlementGuarantee, EntitlementKindId
from ffun.subscriptions.domain import new_subscription_id
from ffun.subscriptions.tests.make import make_provider_subscription_reference


class TestBenefitEntitlementAction:
    def test_values_are_stable(self) -> None:
        assert [(action.name, action.value) for action in BenefitEntitlementAction] == [
            ("grant", 1),
            ("revoke", 2),
        ]


class TestBenefitParameterDefinition:
    def test_validate_bounds__accepts_equal_bounds(self) -> None:
        BenefitParameterDefinition(
            id=BenefitParameterId("quantity"),
            minimum=10,
            maximum=10,
        )

    def test_validate_bounds__rejects_reversed_bounds(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="minimum must not exceed maximum"):
            BenefitParameterDefinition(
                id=BenefitParameterId("quantity"),
                minimum=20,
                maximum=10,
            )


class TestParameterConstant:
    def test_materialize__returns_constant(self) -> None:
        value_template = ParameterConstant(value=42)

        assert value_template.materialize({BenefitParameterId("ignored"): 100}) == 42

    @pytest.mark.parametrize("value", [None, True, 1.5, "1", 0, -1, MAX_ENTITLEMENT_VALUE + 1])
    def test_init__value_must_be_persistence_safe_integer(self, value: object) -> None:
        with pytest.raises(pydantic.ValidationError):
            ParameterConstant(value=cast(int, value))


class TestParameterReference:
    def test_materialize__returns_referenced_parameter(self) -> None:
        parameter_id = BenefitParameterId("quantity")
        value_template = ParameterReference(parameter_id=parameter_id)

        assert value_template.materialize({parameter_id: 42}) == 42

    def test_materialize__unknown_parameter(self) -> None:
        parameter_id = BenefitParameterId("quantity")
        value_template = ParameterReference(parameter_id=parameter_id)

        with pytest.raises(errors.MissingBenefitParameter) as exception_info:
            value_template.materialize({})

        attributes = cast(dict[str, object], vars(exception_info.value))
        assert attributes["parameter_id"] == parameter_id
        assert isinstance(exception_info.value.__cause__, KeyError)


class TestBenefitPackage:
    def test_parameters__defaults_to_empty(self) -> None:
        assert make_benefit_package().parameters == {}

    def test_init__requires_entitlements(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="at least 1 item"):
            make_benefit_package(entitlements={})

    def test_model_dump__serializes_mappings(self) -> None:
        package = make_benefit_package(
            parameters={BenefitParameterId("quantity"): 10},
            entitlements={EntitlementKindId.lifetime_tokens: 10},
        )

        assert cast(dict[str, object], package.model_dump()) == {
            "id": "test-benefit",
            "parameters": {"quantity": 10},
            "entitlements": {EntitlementKindId.lifetime_tokens: 10},
        }

    def test_guarantees__orders_by_entitlement_kind(self) -> None:
        package = make_benefit_package(
            entitlements={
                EntitlementKindId.lifetime_tokens: 30,
                EntitlementKindId.day_tokens: 10,
                EntitlementKindId.month_tokens: 20,
            }
        )

        assert package.guarantees == (
            EntitlementGuarantee(kind_id=EntitlementKindId.day_tokens, value=10),
            EntitlementGuarantee(kind_id=EntitlementKindId.month_tokens, value=20),
            EntitlementGuarantee(kind_id=EntitlementKindId.lifetime_tokens, value=30),
        )


class TestBenefitPackageTemplate:
    def test_init__parses_both_value_template_variants(self) -> None:
        template = BenefitPackageTemplate.model_validate_json(
            """
            {
                "id": "supporter",
                "title": "Supporter",
                "description": "Parameterized package",
                "parameters": [{"id": "quantity", "minimum": 1, "maximum": 100}],
                "entitlements": {
                    "3": {"parameter_id": "quantity"},
                    "1": {"value": 10}
                }
            }
            """
        )

        assert template.entitlements == {
            EntitlementKindId.lifetime_tokens: ParameterReference(parameter_id=BenefitParameterId("quantity")),
            EntitlementKindId.day_tokens: ParameterConstant(value=10),
        }

    def test_init__requires_entitlement_templates(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="at least 1 item"):
            BenefitPackageTemplate(
                id=BenefitId("empty"),
                title=NonEmptyString("Empty"),
                description="No guarantees",
                entitlements={},
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
