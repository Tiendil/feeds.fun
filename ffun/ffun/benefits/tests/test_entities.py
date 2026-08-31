import datetime
from typing import cast

import pydantic
import pytest
from pytest_mock import MockerFixture

from ffun.benefits import errors
from ffun.benefits.entities import (
    ADMIN_BENEFIT_SOURCE_ID,
    BenefitEntitlementAction,
    BenefitPackageTemplate,
    BenefitParameterDefinition,
    BenefitParameterId,
    BenefitSourceId,
    BenefitSubscriptionRefreshCommand,
    BenefitTransaction,
    InternalTarget,
    NewTarget,
    ParameterConstant,
    ParameterReference,
    TargetKind,
)
from ffun.benefits.tests.make import (
    make_benefit_package,
    make_benefit_package_template,
    make_benefit_transaction,
    make_external_target,
    make_one_time_purchase_benefit_transaction,
    make_transaction_command,
)
from ffun.core.entities import NonEmptyString
from ffun.domain.entities import BenefitId
from ffun.entitlements import entities as entitlement_entities
from ffun.entitlements.entities import MAX_ENTITLEMENT_VALUE, EntitlementGuarantee, EntitlementKindId
from ffun.one_time_purchases.domain import new_purchase_id
from ffun.subscriptions.domain import new_subscription_id
from ffun.subscriptions.tests.make import make_provider_subscription_reference


class TestBenefitSourceId:
    def test_admin_stable_value(self) -> None:
        assert ADMIN_BENEFIT_SOURCE_ID == BenefitSourceId(1)


class TestBenefitEntitlementAction:
    def test_values_are_stable(self) -> None:
        assert [(action.name, action.value) for action in BenefitEntitlementAction] == [
            ("grant", 1),
            ("revoke", 2),
        ]


class TestTargetKind:
    def test_values_are_stable(self) -> None:
        assert [(kind.name, kind.value) for kind in TargetKind] == [
            ("internal", "internal"),
            ("external", "external"),
            ("new", "new"),
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

    def test_validate_value__accepts_boundary_values(self) -> None:
        definition = BenefitParameterDefinition(
            id=BenefitParameterId("quantity"),
            minimum=10,
            maximum=20,
        )

        definition.validate_value(10)
        definition.validate_value(20)

    @pytest.mark.parametrize("value", [None, True, 1.5, "10"])
    def test_validate_value__rejects_non_strict_integers(self, value: object) -> None:
        definition = BenefitParameterDefinition(
            id=BenefitParameterId("quantity"),
            minimum=1,
            maximum=100,
        )

        with pytest.raises(errors.InvalidBenefitParameter) as exception_info:
            definition.validate_value(value)

        attributes = cast(dict[str, object], vars(exception_info.value))
        assert attributes["parameter_id"] == definition.id
        assert attributes["value_type"] == type(value).__name__

    @pytest.mark.parametrize("value", [9, 21])
    def test_validate_value__rejects_value_outside_configured_bounds(self, value: int) -> None:
        definition = BenefitParameterDefinition(
            id=BenefitParameterId("quantity"),
            minimum=10,
            maximum=20,
        )

        with pytest.raises(errors.InvalidBenefitParameter) as exception_info:
            definition.validate_value(value)

        attributes = cast(dict[str, object], vars(exception_info.value))
        assert attributes["parameter_id"] == definition.id
        assert attributes["value"] == value
        assert attributes["minimum"] == definition.minimum
        assert attributes["maximum"] == definition.maximum


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
                    "lifetime_tokens": {"parameter_id": "quantity"},
                    "day_tokens": {"value": 10}
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

    def test_parameter_ids_must_be_unique__rejects_duplicate_ids(self) -> None:
        parameter = BenefitParameterDefinition(
            id=BenefitParameterId("quantity"),
            minimum=1,
            maximum=100,
        )

        with pytest.raises(pydantic.ValidationError, match="parameter ids must be unique"):
            make_benefit_package_template(
                parameters=(parameter, parameter),
                entitlements={EntitlementKindId.lifetime_tokens: ParameterReference(parameter_id=parameter.id)},
            )

    def test_parameter_references_must_be_valid__rejects_undeclared_reference(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="references undeclared parameters: quantity"):
            make_benefit_package_template(
                entitlements={
                    EntitlementKindId.lifetime_tokens: ParameterReference(parameter_id=BenefitParameterId("quantity"))
                },
            )

    def test_parameter_references_must_be_valid__rejects_unused_parameter(self) -> None:
        parameter = BenefitParameterDefinition(
            id=BenefitParameterId("quantity"),
            minimum=1,
            maximum=100,
        )

        with pytest.raises(pydantic.ValidationError, match="has unused parameters: quantity"):
            make_benefit_package_template(parameters=(parameter,))

    def test_constant_values_must_match_entitlement_kinds__rejects_incompatible_constant(
        self,
        mocker: MockerFixture,
    ) -> None:
        day_tokens = entitlement_entities.ENTITLEMENT_KINDS[0].replace(minimum_value=10, maximum_value=20)
        mocker.patch.object(
            entitlement_entities,
            "ENTITLEMENT_KINDS",
            (day_tokens, *entitlement_entities.ENTITLEMENT_KINDS[1:]),
        )

        with pytest.raises(
            pydantic.ValidationError,
            match="constant for day_tokens must be within entitlement kind bounds",
        ):
            make_benefit_package_template(entitlements={EntitlementKindId.day_tokens: ParameterConstant(value=9)})

    def test_parameter_ranges_must_match_entitlement_kinds__rejects_incompatible_range(
        self,
        mocker: MockerFixture,
    ) -> None:
        day_tokens = entitlement_entities.ENTITLEMENT_KINDS[0].replace(minimum_value=10, maximum_value=20)
        mocker.patch.object(
            entitlement_entities,
            "ENTITLEMENT_KINDS",
            (day_tokens, *entitlement_entities.ENTITLEMENT_KINDS[1:]),
        )
        parameter = BenefitParameterDefinition(
            id=BenefitParameterId("quantity"),
            minimum=9,
            maximum=20,
        )

        with pytest.raises(pydantic.ValidationError, match="parameter quantity range for day_tokens"):
            make_benefit_package_template(
                parameters=(parameter,),
                entitlements={EntitlementKindId.day_tokens: ParameterReference(parameter_id=parameter.id)},
            )

    def test_materialize__resolves_parameters_and_constants(self) -> None:
        parameter = BenefitParameterDefinition(
            id=BenefitParameterId("quantity"),
            minimum=1,
            maximum=100,
        )
        template = make_benefit_package_template(
            parameters=(parameter,),
            entitlements={
                EntitlementKindId.month_tokens: ParameterConstant(value=42),
                EntitlementKindId.lifetime_tokens: ParameterReference(parameter_id=parameter.id),
            },
        )

        package = template.materialize({parameter.id: 25})

        assert package.id == template.id
        assert package.parameters == {parameter.id: 25}
        assert package.entitlements == {
            EntitlementKindId.month_tokens: 42,
            EntitlementKindId.lifetime_tokens: 25,
        }

    def test_materialize__parameterless_template_requires_empty_parameters(self) -> None:
        template = make_benefit_package_template()

        assert template.materialize({}) == make_benefit_package()

    def test_materialize__rejects_missing_parameter(self) -> None:
        parameter = BenefitParameterDefinition(
            id=BenefitParameterId("quantity"),
            minimum=1,
            maximum=100,
        )
        template = make_benefit_package_template(
            parameters=(parameter,),
            entitlements={EntitlementKindId.lifetime_tokens: ParameterReference(parameter_id=parameter.id)},
        )

        with pytest.raises(errors.MissingBenefitParameter) as exception_info:
            template.materialize({})

        attributes = cast(dict[str, object], vars(exception_info.value))
        assert attributes["parameter_id"] == parameter.id

    def test_materialize__rejects_unknown_parameter(self) -> None:
        template = make_benefit_package_template()
        parameter_id = BenefitParameterId("unknown")

        with pytest.raises(errors.UnknownBenefitParameter) as exception_info:
            template.materialize({parameter_id: 10})

        attributes = cast(dict[str, object], vars(exception_info.value))
        assert attributes["parameter_id"] == parameter_id

    def test_materialize__validates_resolved_entitlement_against_current_kind(
        self,
        mocker: MockerFixture,
    ) -> None:
        template = make_benefit_package_template()
        day_tokens = entitlement_entities.ENTITLEMENT_KINDS[0].replace(minimum_value=11)
        mocker.patch.object(
            entitlement_entities,
            "ENTITLEMENT_KINDS",
            (day_tokens, *entitlement_entities.ENTITLEMENT_KINDS[1:]),
        )

        with pytest.raises(errors.InvalidBenefitEntitlement) as exception_info:
            template.materialize({})

        attributes = cast(dict[str, object], vars(exception_info.value))
        assert attributes["benefit_id"] == template.id
        assert attributes["entitlement_kind_id"] == EntitlementKindId.day_tokens
        assert attributes["value"] == 10
        assert isinstance(exception_info.value.__cause__, ValueError)


class TestInternalTarget:
    def test_kind__uses_enum_and_preserves_serialized_value(self) -> None:
        target = InternalTarget(internal_id=new_subscription_id())

        assert target.kind == TargetKind.internal
        assert cast(dict[str, object], target.model_dump(mode="json"))["kind"] == "internal"

    def test_provider_reference__is_missing(self) -> None:
        target = InternalTarget(internal_id=new_subscription_id())

        assert target.provider_reference is None


class TestExternalTarget:
    def test_kind__uses_enum_and_preserves_serialized_value(self) -> None:
        target = make_external_target()

        assert target.kind == TargetKind.external
        assert cast(dict[str, object], target.model_dump(mode="json"))["kind"] == "external"

    def test_provider_reference__contains_external_identity(self) -> None:
        reference = make_provider_subscription_reference()
        target = make_external_target(reference)

        assert target.provider_reference == reference

    def test_identity__returns_ordered_external_identity(self) -> None:
        target = make_external_target()

        assert target.identity == (
            target.provider_id,
            target.provider_account_id,
            target.provider_object_id,
        )


class TestNewTarget:
    def test_kind__uses_enum_and_preserves_serialized_value(self) -> None:
        target = NewTarget()

        assert target.kind == TargetKind.new
        assert cast(dict[str, object], target.model_dump(mode="json"))["kind"] == "new"

    def test_provider_reference__is_missing(self) -> None:
        assert NewTarget().provider_reference is None


class TestBenefitTransactionCommand:
    def test_source_identity__returns_source_tuple(self) -> None:
        command = make_transaction_command()

        assert command.source_identity == (command.source_id, command.source_transaction_id)

    def test_effective_at_must_have_timezone__rejects_naive_timestamp(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="effective timestamp must have a UTC offset"):
            make_transaction_command(effective_at=datetime.datetime.now())


class TestBenefitSubscriptionRefreshCommand:
    def test_effective_at_must_have_timezone__rejects_naive_timestamp(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="refresh timestamp must have a UTC offset"):
            BenefitSubscriptionRefreshCommand(
                source_id=ADMIN_BENEFIT_SOURCE_ID,
                benefit_id=BenefitId("test-benefit"),
                effective_at=datetime.datetime.now(),
            )


class TestBenefitTransaction:
    def test_source_identity__returns_source_tuple(self) -> None:
        transaction = make_benefit_transaction()

        assert transaction.source_identity == (transaction.source_id, transaction.source_transaction_id)

    def test_get_subscription_id_or_raise__returns_subscription_id(self) -> None:
        transaction = make_benefit_transaction()

        assert transaction.get_subscription_id_or_raise() == transaction.subscription_id

    def test_get_subscription_id_or_raise__rejects_purchase(self) -> None:
        transaction = make_one_time_purchase_benefit_transaction()

        with pytest.raises(errors.InvalidBenefitTransactionTarget) as exception_info:
            transaction.get_subscription_id_or_raise()

        message = str(exception_info.value)
        assert f"transaction_id={transaction.id}" in message
        assert "expected_target=subscription" in message
        assert "actual_target=one_time_purchase" in message

    def test_get_one_time_purchase_id_or_raise__returns_purchase_id(self) -> None:
        transaction = make_one_time_purchase_benefit_transaction()

        assert transaction.get_one_time_purchase_id_or_raise() == transaction.one_time_purchase_id

    def test_get_one_time_purchase_id_or_raise__rejects_subscription(self) -> None:
        transaction = make_benefit_transaction()

        with pytest.raises(errors.InvalidBenefitTransactionTarget) as exception_info:
            transaction.get_one_time_purchase_id_or_raise()

        message = str(exception_info.value)
        assert f"transaction_id={transaction.id}" in message
        assert "expected_target=one_time_purchase" in message
        assert "actual_target=subscription" in message

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

    @pytest.mark.parametrize("with_both_targets", [False, True])
    def test_validate_target__requires_exactly_one_target(self, with_both_targets: bool) -> None:
        transaction = make_benefit_transaction()
        data = cast(dict[str, object], transaction.model_dump())
        data["subscription_id"] = transaction.subscription_id if with_both_targets else None
        data["one_time_purchase_id"] = new_purchase_id() if with_both_targets else None

        with pytest.raises(pydantic.ValidationError, match="must have exactly one target"):
            BenefitTransaction.model_validate(data)

    def test_validate_one_time_purchase_period_end__requires_lifetime_marker(self) -> None:
        transaction = make_one_time_purchase_benefit_transaction()
        data = cast(dict[str, object], transaction.model_dump())
        data["period_ends_at"] = transaction.period_starts_at + datetime.timedelta(days=1)

        with pytest.raises(pydantic.ValidationError, match="period end must equal lifetime interval end marker"):
            BenefitTransaction.model_validate(data)
