import asyncio
import datetime
import uuid
from collections.abc import Callable
from typing import cast

import pytest
from pytest_mock import MockerFixture

from ffun.audit.entities import AuditEntityKind
from ffun.benefits import domain, errors, operations, target_resolution
from ffun.benefits.entities import (
    ADMIN_BENEFIT_SOURCE_ID,
    BenefitEntitlementAction,
    BenefitPackageTemplate,
    BenefitParameterDefinition,
    BenefitParameterId,
    BenefitSourceId,
    BenefitSourceTransactionId,
    BenefitSubscriptionRefreshCommand,
    BenefitSubscriptionRefreshOutcome,
    BenefitSubscriptionRefreshResult,
    BenefitTransaction,
    BenefitTransactionApplicationResult,
    BenefitTransactionCommand,
    InternalTarget,
    ParameterConstant,
    ParameterReference,
)
from ffun.benefits.tests.make import (
    make_benefit_package,
    make_benefit_package_template,
    make_benefit_transaction,
    make_external_target,
    make_one_time_purchase_benefit_transaction,
    make_one_time_purchase_transaction_command,
    make_subscription_snapshot,
    make_transaction_command,
)
from ffun.core.postgresql import ExecuteType, TransactionExecuteType, execute, transaction
from ffun.core.tests.helpers import (
    TableSizeDelta,
    TableSizeNotChanged,
    assert_logs_has_business_event,
    assert_logs_has_no_business_event,
    assert_pool_capacity_at_least,
    capture_logs,
)
from ffun.domain.datetime_intervals import LIFETIME_INTERVAL_END_MARKER
from ffun.domain.entities import (
    BenefitId,
    BenefitTransactionId,
    OneTimePurchaseId,
    ProviderStatus,
    PurchasedStateSaveOutcome,
    SerializedId,
    SubscriptionId,
)
from ffun.entitlements import domain as entitlement_domain
from ffun.entitlements.entities import EntitlementGuarantee, EntitlementKindId
from ffun.entitlements.tests import helpers as entitlement_helpers
from ffun.entitlements.tests.make import make_source_entitlement
from ffun.one_time_purchases import domain as purchase_domain
from ffun.one_time_purchases.entities import PurchaseSaveResult, PurchaseSnapshot, PurchaseStatus
from ffun.one_time_purchases.tests.make import make_provider_purchase_reference, make_purchase_snapshot
from ffun.subscriptions import domain as subscription_domain
from ffun.subscriptions.entities import SubscriptionSaveResult, SubscriptionSnapshot, SubscriptionStatusId
from ffun.subscriptions.tests.make import make_provider_subscription_reference

_ACTOR_KIND = AuditEntityKind.psp
_ACTOR_ID = SerializedId("provider-hook")
_QUANTITY_PARAMETER_ID = BenefitParameterId("quantity")


@pytest.fixture  # type: ignore[misc]
def package(mocker: MockerFixture) -> BenefitPackageTemplate:
    configured = make_benefit_package_template()
    mocker.patch.object(domain.settings, "package_templates", (configured,))
    return configured


@pytest.fixture  # type: ignore[misc]
def purchase_package(mocker: MockerFixture) -> BenefitPackageTemplate:
    configured = make_benefit_package_template(
        parameters=(
            BenefitParameterDefinition(
                id=_QUANTITY_PARAMETER_ID,
                minimum=1,
                maximum=1_000_000,
            ),
        ),
        entitlements={
            EntitlementKindId.lifetime_tokens: ParameterReference(parameter_id=_QUANTITY_PARAMETER_ID),
        },
    )
    mocker.patch.object(domain.settings, "package_templates", (configured,))
    return configured


async def _apply(
    subscription: SubscriptionSnapshot,
    command: BenefitTransactionCommand[SubscriptionId],
) -> BenefitTransactionApplicationResult[SubscriptionId]:
    return await domain.apply_subscription_transaction(
        subscription,
        command,
        actor_kind=_ACTOR_KIND,
        actor_id=_ACTOR_ID,
    )


async def _apply_purchase(
    purchase: PurchaseSnapshot,
    parameters: dict[BenefitParameterId, object],
    command: BenefitTransactionCommand[OneTimePurchaseId],
) -> BenefitTransactionApplicationResult[OneTimePurchaseId]:
    return await domain.apply_one_time_purchase_transaction(
        purchase,
        parameters,
        command,
        actor_kind=_ACTOR_KIND,
        actor_id=_ACTOR_ID,
    )


class TestGetBenefitTransaction:
    @pytest.mark.asyncio
    async def test_missing(self) -> None:
        assert await domain.get_benefit_transaction(BenefitTransactionId(uuid.uuid4())) is None

    @pytest.mark.asyncio
    async def test_loads_persisted_transaction(self) -> None:
        benefit_transaction = make_benefit_transaction()
        await operations.save_benefit_transaction(execute, benefit_transaction)

        assert await domain.get_benefit_transaction(benefit_transaction.id) == benefit_transaction


class TestFindBenefit:
    def test_returns_configured_template(self, package: BenefitPackageTemplate) -> None:
        assert domain._find_benefit(package.id) == package

    def test_unknown_identifier(self, package: BenefitPackageTemplate) -> None:
        assert domain._find_benefit(BenefitId("unknown")) is None


class TestGetBenefit:
    def test_returns_configured_template(self, package: BenefitPackageTemplate) -> None:
        assert domain.get_benefit(package.id) == package

    def test_unknown_identifier_raises_module_error(self, package: BenefitPackageTemplate) -> None:
        with pytest.raises(errors.UnknownBenefit) as exception_info:
            domain.get_benefit(BenefitId("unknown"))

        assert "benefit_id=unknown" in str(exception_info.value)


class TestHasBenefit:
    def test_configured_identifier(self, package: BenefitPackageTemplate) -> None:
        assert domain.has_benefit(package.id)

    def test_unknown_identifier(self, package: BenefitPackageTemplate) -> None:
        assert not domain.has_benefit(BenefitId("unknown"))


class TestMaterializeBenefitPackage:
    def test_materializes_configured_template(self, mocker: MockerFixture) -> None:
        parameter = BenefitParameterDefinition(
            id=BenefitParameterId("quantity"),
            minimum=1,
            maximum=100,
        )
        template = make_benefit_package_template(
            parameters=(parameter,),
            entitlements={EntitlementKindId.lifetime_tokens: ParameterReference(parameter_id=parameter.id)},
        )
        mocker.patch.object(domain.settings, "package_templates", (template,))

        assert domain.materialize_benefit_package(template.id, {parameter.id: 25}) == make_benefit_package(
            benefit_id=template.id,
            parameters={parameter.id: 25},
            entitlements={EntitlementKindId.lifetime_tokens: 25},
        )

    def test_unknown_identifier_raises_module_error(self, package: BenefitPackageTemplate) -> None:
        with pytest.raises(errors.UnknownBenefit):
            domain.materialize_benefit_package(BenefitId("unknown"), {})


class TestApplicationResult:
    def test_shapes_subscription_result(self) -> None:
        benefit_transaction = make_benefit_transaction()
        subscription_id = benefit_transaction.get_subscription_id_or_raise()

        assert domain._application_result(
            benefit_transaction,
            subscription_id,
            created=True,
        ) == BenefitTransactionApplicationResult(
            transaction_id=benefit_transaction.id,
            transaction_created=True,
            target_id=subscription_id,
        )

    def test_shapes_one_time_purchase_result(self) -> None:
        benefit_transaction = make_one_time_purchase_benefit_transaction()
        one_time_purchase_id = benefit_transaction.get_one_time_purchase_id_or_raise()

        assert domain._application_result(
            benefit_transaction,
            one_time_purchase_id,
            created=False,
        ) == BenefitTransactionApplicationResult(
            transaction_id=benefit_transaction.id,
            transaction_created=False,
            target_id=one_time_purchase_id,
        )


class TestValidatePackageForInterval:
    @pytest.mark.parametrize(
        ("kind_id", "period_ends_at"),
        [
            (EntitlementKindId.day_tokens, datetime.datetime.now(tz=datetime.UTC)),
            (EntitlementKindId.lifetime_tokens, LIFETIME_INTERVAL_END_MARKER),
        ],
    )
    def test_matching_lifetime_status(
        self,
        kind_id: EntitlementKindId,
        period_ends_at: datetime.datetime,
    ) -> None:
        package = make_benefit_package(
            entitlements={kind_id: 10},
        )

        domain._validate_package_for_interval(package, period_ends_at)

    @pytest.mark.parametrize(
        ("kind_id", "period_ends_at"),
        [
            (EntitlementKindId.day_tokens, LIFETIME_INTERVAL_END_MARKER),
            (EntitlementKindId.lifetime_tokens, datetime.datetime.now(tz=datetime.UTC)),
        ],
    )
    def test_mismatching_lifetime_status(
        self,
        kind_id: EntitlementKindId,
        period_ends_at: datetime.datetime,
    ) -> None:
        package = make_benefit_package(
            entitlements={kind_id: 10},
        )

        with pytest.raises(errors.InvalidBenefitEntitlement) as exception_info:
            domain._validate_package_for_interval(package, period_ends_at)

        attributes = cast(dict[str, object], vars(exception_info.value))
        assert attributes["benefit_id"] == package.id
        assert attributes["entitlement_kind_id"] == kind_id
        assert attributes["reason"] == "entitlement kind lifetime status must match the benefit period"


class TestApplyBenefitTransaction:
    @pytest.mark.asyncio
    async def test_new_transaction_actualizes_and_emits_callbacks(self) -> None:
        command = make_transaction_command()
        benefit_transaction = make_benefit_transaction(
            source_id=command.source_id,
            source_transaction_id=command.source_transaction_id,
        )
        actualize_calls: list[tuple[TransactionExecuteType, datetime.datetime]] = []
        callback_calls = 0

        def callback() -> None:
            nonlocal callback_calls
            callback_calls += 1

        async def actualize(
            actualize_execute: TransactionExecuteType,
            evaluation_time: datetime.datetime,
        ) -> tuple[BenefitTransaction, list[Callable[[], None]]]:
            actualize_calls.append((actualize_execute, evaluation_time))
            return benefit_transaction, [callback]

        started_at = datetime.datetime.now(tz=datetime.UTC)
        result = await domain._apply_benefit_transaction(
            command,
            actualize=actualize,
            get_target_id=BenefitTransaction.get_subscription_id_or_raise,
        )
        finished_at = datetime.datetime.now(tz=datetime.UTC)

        assert result == BenefitTransactionApplicationResult(
            transaction_id=benefit_transaction.id,
            transaction_created=True,
            target_id=benefit_transaction.get_subscription_id_or_raise(),
        )
        assert len(actualize_calls) == 1
        actualize_execute, evaluation_time = actualize_calls[0]
        assert callable(actualize_execute)
        assert started_at <= evaluation_time <= finished_at
        assert callback_calls == 1

    @pytest.mark.asyncio
    async def test_stored_transaction_skips_actualization(self) -> None:
        benefit_transaction = make_benefit_transaction()
        command = make_transaction_command(
            source_id=benefit_transaction.source_id,
            source_transaction_id=benefit_transaction.source_transaction_id,
        )
        await operations.save_benefit_transaction(execute, benefit_transaction)
        actualize_called = False

        async def actualize(
            _execute: TransactionExecuteType,
            _evaluation_time: datetime.datetime,
        ) -> tuple[BenefitTransaction, list[Callable[[], None]]]:
            nonlocal actualize_called
            actualize_called = True
            return benefit_transaction, []

        result = await domain._apply_benefit_transaction(
            command,
            actualize=actualize,
            get_target_id=BenefitTransaction.get_subscription_id_or_raise,
        )

        assert result == BenefitTransactionApplicationResult(
            transaction_id=benefit_transaction.id,
            transaction_created=False,
            target_id=benefit_transaction.get_subscription_id_or_raise(),
        )
        assert not actualize_called


class TestRevokeOwnedEntitlements:
    @pytest.mark.asyncio
    async def test_revokes_subscription_entitlements(self, mocker: MockerFixture) -> None:
        benefit_transaction = make_benefit_transaction()
        subscription_id = benefit_transaction.get_subscription_id_or_raise()
        revoke_callback = mocker.stub(name="revoke_callback")
        revoke = mocker.patch.object(
            entitlement_domain,
            "revoke_subscription_entitlements",
            return_value=([], [revoke_callback]),
        )
        revoke_purchase = mocker.patch.object(
            entitlement_domain,
            "revoke_one_time_purchase_entitlements",
        )
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)

        async with transaction() as transaction_execute:
            callbacks = await domain._revoke_owned_entitlements(
                transaction_execute,
                benefit_transaction,
                evaluation_time=evaluation_time,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert callbacks == [revoke_callback]
        revoke.assert_awaited_once_with(
            transaction_execute,
            subscription_id=subscription_id,
            revoked_by_transaction_id=benefit_transaction.id,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )
        revoke_purchase.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_revokes_one_time_purchase_entitlements(self, mocker: MockerFixture) -> None:
        benefit_transaction = make_one_time_purchase_benefit_transaction()
        one_time_purchase_id = benefit_transaction.get_one_time_purchase_id_or_raise()
        revoke_callback = mocker.stub(name="revoke_callback")
        revoke_subscription = mocker.patch.object(
            entitlement_domain,
            "revoke_subscription_entitlements",
        )
        revoke = mocker.patch.object(
            entitlement_domain,
            "revoke_one_time_purchase_entitlements",
            return_value=([], [revoke_callback]),
        )
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)

        async with transaction() as transaction_execute:
            callbacks = await domain._revoke_owned_entitlements(
                transaction_execute,
                benefit_transaction,
                evaluation_time=evaluation_time,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert callbacks == [revoke_callback]
        revoke_subscription.assert_not_awaited()
        revoke.assert_awaited_once_with(
            transaction_execute,
            one_time_purchase_id=one_time_purchase_id,
            revoked_by_transaction_id=benefit_transaction.id,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )


class TestReplaceBenefit:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "benefit_transaction",
        [
            pytest.param(make_benefit_transaction(), id="subscription"),
            pytest.param(make_one_time_purchase_benefit_transaction(), id="one_time_purchase"),
        ],
    )
    async def test_grant_action_revokes_owner_then_grants_package(
        self,
        benefit_transaction: BenefitTransaction,
        mocker: MockerFixture,
    ) -> None:
        package = make_benefit_package()
        revoke_callback = mocker.stub(name="revoke_callback")
        grant_callback = mocker.stub(name="grant_callback")
        revoke_callbacks: list[Callable[[], None]] = [revoke_callback]
        revoke = mocker.patch.object(
            domain,
            "_revoke_owned_entitlements",
            return_value=revoke_callbacks,
        )
        grant = mocker.patch.object(
            entitlement_domain,
            "grant_source_entitlements",
            return_value=([], [grant_callback]),
        )
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)

        async with transaction() as transaction_execute:
            callbacks = await domain._replace_benefit(
                transaction_execute,
                benefit_transaction,
                package,
                evaluation_time=evaluation_time,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert callbacks == [revoke_callback, grant_callback]
        revoke.assert_awaited_once_with(
            transaction_execute,
            benefit_transaction,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )
        grant.assert_awaited_once_with(
            transaction_execute,
            grant_transaction_id=benefit_transaction.id,
            user_id=benefit_transaction.user_id,
            subscription_id=benefit_transaction.subscription_id,
            one_time_purchase_id=benefit_transaction.one_time_purchase_id,
            guarantees=(EntitlementGuarantee(kind_id=EntitlementKindId.day_tokens, value=10),),
            starts_at=benefit_transaction.period_starts_at,
            expires_at=benefit_transaction.period_ends_at,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

    @pytest.mark.asyncio
    async def test_revoke_action_only_revokes_owner(self, mocker: MockerFixture) -> None:
        effective_at = datetime.datetime.now(tz=datetime.UTC)
        benefit_transaction = make_benefit_transaction(
            entitlement_action=BenefitEntitlementAction.revoke,
            effective_at=effective_at,
        )
        package = make_benefit_package()
        revoke_callback = mocker.stub(name="revoke_callback")
        revoke_callbacks: list[Callable[[], None]] = [revoke_callback]
        revoke = mocker.patch.object(
            domain,
            "_revoke_owned_entitlements",
            return_value=revoke_callbacks,
        )
        grant = mocker.patch.object(entitlement_domain, "grant_source_entitlements")
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)

        async with transaction() as transaction_execute:
            callbacks = await domain._replace_benefit(
                transaction_execute,
                benefit_transaction,
                package,
                evaluation_time=evaluation_time,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert callbacks == [revoke_callback]
        revoke.assert_awaited_once_with(
            transaction_execute,
            benefit_transaction,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )
        grant.assert_not_awaited()


class TestActualizeSubscriptionTransaction:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (SubscriptionStatusId.active, BenefitEntitlementAction.grant),
            (SubscriptionStatusId.ended, BenefitEntitlementAction.revoke),
        ],
    )
    async def test_builds_transaction_with_derived_action_and_combines_callbacks(
        self,
        package: BenefitPackageTemplate,
        mocker: MockerFixture,
        status: SubscriptionStatusId,
        expected: BenefitEntitlementAction,
    ) -> None:
        snapshot = make_subscription_snapshot(benefit_id=package.id, status=status)
        command = make_transaction_command()
        subscription_id = subscription_domain.new_subscription_id()
        transaction_id = BenefitTransactionId(uuid.uuid4())
        subscription_callback: Callable[[], None] = mocker.stub(name="subscription_callback")
        entitlement_callback: Callable[[], None] = mocker.stub(name="entitlement_callback")
        mocker.patch.object(target_resolution, "resolve_subscription_target", return_value=subscription_id)
        mocker.patch.object(operations, "new_benefit_transaction_id", return_value=transaction_id)
        save_transaction = mocker.patch.object(operations, "save_benefit_transaction")
        save_subscription = mocker.patch.object(
            subscription_domain,
            "save_subscription",
            return_value=(
                SubscriptionSaveResult(
                    outcome=PurchasedStateSaveOutcome.created,
                    current=snapshot.with_identity(
                        subscription_id=subscription_id,
                        state_transaction_id=transaction_id,
                    ),
                ),
                subscription_callback,
            ),
        )
        entitlement_callbacks: list[Callable[[], None]] = [entitlement_callback]
        mocker.patch.object(domain, "_replace_benefit", return_value=entitlement_callbacks)

        async with transaction() as transaction_execute:
            benefit_transaction, callbacks = await domain._actualize_subscription_transaction(
                command,
                transaction_execute,
                snapshot,
                evaluation_time=datetime.datetime.now(tz=datetime.UTC),
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert benefit_transaction == make_benefit_transaction(
            transaction_id=transaction_id,
            source_id=command.source_id,
            source_transaction_id=command.source_transaction_id,
            entitlement_action=expected,
            user_id=snapshot.user_id,
            benefit_id=package.id,
            subscription_id=subscription_id,
            effective_at=command.effective_at,
            period_starts_at=snapshot.period_starts_at,
            period_ends_at=snapshot.period_ends_at,
        )
        assert callbacks == [subscription_callback, entitlement_callback]
        save_transaction.assert_awaited_once_with(transaction_execute, benefit_transaction)
        save_subscription.assert_awaited_once_with(
            transaction_execute,
            subscription_id,
            transaction_id,
            snapshot,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

    @pytest.mark.asyncio
    async def test_stale_subscription_raises_before_entitlement_replacement(
        self,
        package: BenefitPackageTemplate,
        mocker: MockerFixture,
    ) -> None:
        snapshot = make_subscription_snapshot(benefit_id=package.id)
        command = make_transaction_command()
        subscription_id = subscription_domain.new_subscription_id()
        transaction_id = BenefitTransactionId(uuid.uuid4())
        current = snapshot.replace(
            provider_updated_at=snapshot.provider_updated_at + datetime.timedelta(seconds=1)
        ).with_identity(
            subscription_id=subscription_id,
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
        )
        mocker.patch.object(target_resolution, "resolve_subscription_target", return_value=subscription_id)
        mocker.patch.object(operations, "new_benefit_transaction_id", return_value=transaction_id)
        mocker.patch.object(operations, "save_benefit_transaction")
        mocker.patch.object(
            subscription_domain,
            "save_subscription",
            return_value=(
                SubscriptionSaveResult(outcome=PurchasedStateSaveOutcome.stale, current=current),
                mocker.stub(name="subscription_callback"),
            ),
        )
        replace = mocker.patch.object(domain, "_replace_benefit")

        with pytest.raises(errors.StaleBenefitTransaction) as exception_info:
            async with transaction() as transaction_execute:
                await domain._actualize_subscription_transaction(
                    command,
                    transaction_execute,
                    snapshot,
                    evaluation_time=datetime.datetime.now(tz=datetime.UTC),
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        message = str(exception_info.value)
        assert f"subscription_id={subscription_id}" in message
        assert f"incoming_provider_updated_at={snapshot.provider_updated_at.isoformat()}" in message
        assert f"current_provider_updated_at={current.provider_updated_at.isoformat()}" in message
        replace.assert_not_awaited()


class TestActualizeOneTimePurchaseTransaction:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            (PurchaseStatus.completed, BenefitEntitlementAction.grant),
            (PurchaseStatus.refunded, BenefitEntitlementAction.revoke),
        ],
    )
    async def test_builds_transaction_with_derived_action_and_combines_callbacks(
        self,
        purchase_package: BenefitPackageTemplate,
        mocker: MockerFixture,
        status: PurchaseStatus,
        expected: BenefitEntitlementAction,
    ) -> None:
        snapshot = make_purchase_snapshot(benefit_id=purchase_package.id, status=status)
        command = make_one_time_purchase_transaction_command()
        purchase_id = purchase_domain.new_purchase_id()
        transaction_id = BenefitTransactionId(uuid.uuid4())
        purchase_callback: Callable[[], None] = mocker.stub(name="purchase_callback")
        entitlement_callback: Callable[[], None] = mocker.stub(name="entitlement_callback")
        mocker.patch.object(target_resolution, "resolve_one_time_purchase_target", return_value=purchase_id)
        mocker.patch.object(operations, "new_benefit_transaction_id", return_value=transaction_id)
        save_transaction = mocker.patch.object(operations, "save_benefit_transaction")
        save_purchase = mocker.patch.object(
            purchase_domain,
            "save_purchase",
            return_value=(
                PurchaseSaveResult(
                    outcome=PurchasedStateSaveOutcome.created,
                    current=snapshot.with_identity(
                        one_time_purchase_id=purchase_id,
                        state_transaction_id=transaction_id,
                    ),
                ),
                purchase_callback,
            ),
        )
        entitlement_callbacks: list[Callable[[], None]] = [entitlement_callback]
        mocker.patch.object(domain, "_replace_benefit", return_value=entitlement_callbacks)

        async with transaction() as transaction_execute:
            benefit_transaction, callbacks = await domain._actualize_one_time_purchase_transaction(
                command,
                transaction_execute,
                snapshot,
                {_QUANTITY_PARAMETER_ID: 100},
                evaluation_time=datetime.datetime.now(tz=datetime.UTC),
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert benefit_transaction == make_one_time_purchase_benefit_transaction(
            transaction_id=transaction_id,
            source_id=command.source_id,
            source_transaction_id=command.source_transaction_id,
            entitlement_action=expected,
            user_id=snapshot.user_id,
            benefit_id=purchase_package.id,
            one_time_purchase_id=purchase_id,
            effective_at=command.effective_at,
            period_starts_at=snapshot.period_starts_at,
            period_ends_at=snapshot.period_ends_at,
        )
        assert callbacks == [purchase_callback, entitlement_callback]
        save_transaction.assert_awaited_once_with(transaction_execute, benefit_transaction)
        save_purchase.assert_awaited_once_with(
            transaction_execute,
            purchase_id,
            transaction_id,
            snapshot,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

    @pytest.mark.asyncio
    async def test_stale_purchase_raises_before_entitlement_replacement(
        self,
        purchase_package: BenefitPackageTemplate,
        mocker: MockerFixture,
    ) -> None:
        snapshot = make_purchase_snapshot(benefit_id=purchase_package.id)
        command = make_one_time_purchase_transaction_command()
        purchase_id = purchase_domain.new_purchase_id()
        transaction_id = BenefitTransactionId(uuid.uuid4())
        current = snapshot.replace(
            provider_updated_at=snapshot.provider_updated_at + datetime.timedelta(seconds=1)
        ).with_identity(
            one_time_purchase_id=purchase_id,
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
        )
        mocker.patch.object(target_resolution, "resolve_one_time_purchase_target", return_value=purchase_id)
        mocker.patch.object(operations, "new_benefit_transaction_id", return_value=transaction_id)
        mocker.patch.object(operations, "save_benefit_transaction")
        mocker.patch.object(
            purchase_domain,
            "save_purchase",
            return_value=(
                PurchaseSaveResult(outcome=PurchasedStateSaveOutcome.stale, current=current),
                mocker.stub(name="purchase_callback"),
            ),
        )
        replace = mocker.patch.object(domain, "_replace_benefit")

        with pytest.raises(errors.StaleBenefitTransaction) as exception_info:
            async with transaction() as transaction_execute:
                await domain._actualize_one_time_purchase_transaction(
                    command,
                    transaction_execute,
                    snapshot,
                    {_QUANTITY_PARAMETER_ID: 100},
                    evaluation_time=datetime.datetime.now(tz=datetime.UTC),
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        message = str(exception_info.value)
        assert f"one_time_purchase_id={purchase_id}" in message
        assert f"incoming_provider_updated_at={snapshot.provider_updated_at.isoformat()}" in message
        assert f"current_provider_updated_at={current.provider_updated_at.isoformat()}" in message
        replace.assert_not_awaited()


class TestApplySubscriptionTransaction:
    @pytest.mark.asyncio
    async def test_grant_persists_atomic_state_and_emits_events(self, mocker: MockerFixture) -> None:
        package = make_benefit_package_template(
            entitlements={
                EntitlementKindId.day_tokens: ParameterConstant(value=10),
                EntitlementKindId.month_tokens: ParameterConstant(value=100),
            }
        )
        mocker.patch.object(domain.settings, "package_templates", (package,))
        snapshot = make_subscription_snapshot(benefit_id=package.id, status=SubscriptionStatusId.active)
        command = make_transaction_command()

        with capture_logs() as logs:
            async with (
                TableSizeDelta("b_transactions", delta=1),
                TableSizeDelta("sb_subscriptions", delta=1),
                TableSizeDelta("en_source_entitlements", delta=2),
                TableSizeDelta("en_entitlements", delta=2),
                TableSizeDelta("a_records", delta=3),
            ):
                result = await _apply(snapshot, command)

        assert result.transaction_created
        stored_transaction = await domain.get_benefit_transaction(result.transaction_id)
        assert stored_transaction is not None
        assert stored_transaction.source_identity == command.source_identity
        assert stored_transaction.entitlement_action == BenefitEntitlementAction.grant
        assert stored_transaction.benefit_id == package.id
        assert stored_transaction.period_starts_at == snapshot.period_starts_at
        assert stored_transaction.period_ends_at == snapshot.period_ends_at
        assert await subscription_domain.get_subscription(result.target_id) == snapshot.with_identity(
            subscription_id=result.target_id,
            state_transaction_id=result.transaction_id,
        )

        day_source = await entitlement_helpers.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.day_tokens,
            result.transaction_id,
        )
        month_source = await entitlement_helpers.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.month_tokens,
            result.transaction_id,
        )
        assert day_source is not None
        assert day_source.subscription_id == result.target_id
        assert day_source.value == 10
        assert day_source.starts_at == snapshot.period_starts_at
        assert day_source.expires_at == snapshot.period_ends_at
        assert month_source is not None
        assert month_source.value == 100
        assert month_source.starts_at == snapshot.period_starts_at
        assert month_source.expires_at == snapshot.period_ends_at

        assert_logs_has_business_event(
            logs,
            "subscription_changed",
            user_id=snapshot.user_id,
            subscription_id=str(result.target_id),
            state_transaction_id=str(result.transaction_id),
        )
        assert_logs_has_business_event(
            logs,
            "source_entitlement_changed",
            user_id=snapshot.user_id,
            grant_transaction_id=str(result.transaction_id),
        )
        assert_logs_has_business_event(logs, "entitlement_changed", user_id=snapshot.user_id)
        assert sum(record.get("event") == "subscription_changed" for record in logs) == 1
        assert sum(record.get("event") == "source_entitlement_changed" for record in logs) == 2
        assert sum(record.get("event") == "entitlement_changed" for record in logs) == 2
        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")

    @pytest.mark.asyncio
    async def test_rejects_parameterized_package(self, mocker: MockerFixture) -> None:
        quantity = BenefitParameterDefinition(
            id=BenefitParameterId("quantity"),
            minimum=1,
            maximum=100,
        )
        package = make_benefit_package_template(
            parameters=(quantity,),
            entitlements={
                EntitlementKindId.day_tokens: ParameterConstant(value=10),
                EntitlementKindId.month_tokens: ParameterReference(parameter_id=quantity.id),
            },
        )
        mocker.patch.object(domain.settings, "package_templates", (package,))
        snapshot = make_subscription_snapshot(benefit_id=package.id)
        command = make_transaction_command()

        async with (
            TableSizeNotChanged("b_transactions"),
            TableSizeNotChanged("sb_subscriptions"),
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            with pytest.raises(errors.MissingBenefitParameter) as exception_info:
                await domain.apply_subscription_transaction(
                    snapshot,
                    command,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        attributes = cast(dict[str, object], vars(exception_info.value))
        assert attributes["parameter_id"] == quantity.id

    @pytest.mark.asyncio
    async def test_revoke_is_inferred_from_status_and_replaces_complete_state(
        self,
        mocker: MockerFixture,
    ) -> None:
        original_package = make_benefit_package_template(
            benefit_id=BenefitId("original"),
            entitlements={
                EntitlementKindId.day_tokens: ParameterConstant(value=10),
                EntitlementKindId.month_tokens: ParameterConstant(value=20),
            },
        )
        current_package = make_benefit_package_template(
            benefit_id=BenefitId("current"),
            entitlements={EntitlementKindId.day_tokens: ParameterConstant(value=30)},
        )
        mocker.patch.object(domain.settings, "package_templates", (original_package, current_package))
        original_snapshot = make_subscription_snapshot(benefit_id=original_package.id)
        grant = await _apply(original_snapshot, make_transaction_command())
        application_started_at = datetime.datetime.now(tz=datetime.UTC)
        transaction_effective_at = application_started_at - datetime.timedelta(days=1)
        current_snapshot = original_snapshot.replace(
            benefit_id=current_package.id,
            status=SubscriptionStatusId.ended,
            provider_status=ProviderStatus("canceled"),
            ends_at=application_started_at,
            provider_updated_at=original_snapshot.provider_updated_at + datetime.timedelta(seconds=1),
        )
        command = make_transaction_command(
            target=InternalTarget(internal_id=grant.target_id),
            effective_at=transaction_effective_at,
        )

        with capture_logs() as logs:
            async with (
                TableSizeDelta("b_transactions", delta=1),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeDelta("a_records", delta=3),
            ):
                revocation = await _apply(current_snapshot, command)
        application_finished_at = datetime.datetime.now(tz=datetime.UTC)

        stored = await domain.get_benefit_transaction(revocation.transaction_id)
        assert stored is not None
        assert stored.entitlement_action == BenefitEntitlementAction.revoke
        assert stored.benefit_id == current_package.id
        assert await subscription_domain.get_subscription(grant.target_id) == current_snapshot.with_identity(
            subscription_id=grant.target_id,
            state_transaction_id=revocation.transaction_id,
        )

        for kind_id in original_package.entitlements:
            source = await entitlement_helpers.load_source_entitlement(
                execute,
                original_snapshot.user_id,
                kind_id,
                grant.transaction_id,
            )
            assert source is not None
            assert source.revoked_at is not None
            assert application_started_at <= source.revoked_at <= application_finished_at
            assert source.revoked_by_transaction_id == revocation.transaction_id

        assert (
            await entitlement_helpers.load_source_entitlement(
                execute,
                original_snapshot.user_id,
                EntitlementKindId.day_tokens,
                revocation.transaction_id,
            )
            is None
        )
        assert_logs_has_business_event(logs, "subscription_changed", user_id=original_snapshot.user_id)
        assert sum(record.get("event") == "subscription_changed" for record in logs) == 1
        assert sum(record.get("event") == "source_entitlement_changed" for record in logs) == 2
        assert sum(record.get("event") == "entitlement_changed" for record in logs) == 2
        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")

    @pytest.mark.asyncio
    async def test_external_target_creates_and_reuses_reference(self, mocker: MockerFixture) -> None:
        package = make_benefit_package_template()
        mocker.patch.object(domain.settings, "package_templates", (package,))
        target = make_external_target()
        first_snapshot = make_subscription_snapshot(benefit_id=package.id)
        second_snapshot = first_snapshot.replace(
            provider_updated_at=first_snapshot.provider_updated_at + datetime.timedelta(seconds=1)
        )

        async with TableSizeDelta("sb_subscription_refs", delta=1):
            first = await _apply(
                first_snapshot,
                make_transaction_command(target=target),
            )

        async with TableSizeNotChanged("sb_subscription_refs"):
            second = await _apply(
                second_snapshot,
                make_transaction_command(target=target),
            )

        assert second.target_id == first.target_id
        assert (
            await subscription_domain.load_provider_subscription_reference(execute, target.provider_reference)
            == first.target_id
        )

    @pytest.mark.asyncio
    async def test_source_retry_returns_first_result_and_ignores_new_payload(
        self,
        package: BenefitPackageTemplate,
    ) -> None:
        first_snapshot = make_subscription_snapshot(benefit_id=package.id)
        command = make_transaction_command()
        first = await _apply(first_snapshot, command)
        retry_snapshot = make_subscription_snapshot(benefit_id=BenefitId("unknown"))
        retry_command = make_transaction_command(
            source_id=command.source_id,
            source_transaction_id=command.source_transaction_id,
            target=InternalTarget(internal_id=subscription_domain.new_subscription_id()),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                retry = await _apply(retry_snapshot, retry_command)

        assert retry == first.replace(transaction_created=False)
        assert await subscription_domain.get_subscription(first.target_id) == first_snapshot.with_identity(
            subscription_id=first.target_id,
            state_transaction_id=first.transaction_id,
        )
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_unknown_benefit_rolls_back_all_state(self, package: BenefitPackageTemplate) -> None:
        reference = make_provider_subscription_reference()
        target = make_external_target(reference)
        snapshot = make_subscription_snapshot(benefit_id=BenefitId("unknown"))

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("sb_subscription_refs"),
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(errors.UnknownBenefit):
                    await _apply(snapshot, make_transaction_command(target=target))

        assert await subscription_domain.load_provider_subscription_reference(execute, reference) is None
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_concurrent_source_loser_rolls_back_external_reference(
        self,
        package: BenefitPackageTemplate,
        mocker: MockerFixture,
    ) -> None:
        reference = make_provider_subscription_reference()
        target = make_external_target(reference)
        mocker.patch.object(
            operations,
            "save_benefit_transaction",
            side_effect=errors.ConcurrentBenefitTransaction(),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("sb_subscription_refs"),
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(errors.ConcurrentBenefitTransaction):
                    await _apply(
                        make_subscription_snapshot(benefit_id=package.id),
                        make_transaction_command(target=target),
                    )

        assert await subscription_domain.load_provider_subscription_reference(execute, reference) is None
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_entitlement_failure_rolls_back_transaction_subscription_reference_and_audit(
        self,
        package: BenefitPackageTemplate,
        mocker: MockerFixture,
    ) -> None:
        reference = make_provider_subscription_reference()
        target = make_external_target(reference)
        command = make_transaction_command(target=target)
        mocker.patch.object(
            entitlement_domain,
            "grant_source_entitlements",
            side_effect=RuntimeError("entitlement write failed"),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("sb_subscription_refs"),
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(RuntimeError, match="entitlement write failed"):
                    await _apply(make_subscription_snapshot(benefit_id=package.id), command)

        assert await subscription_domain.load_provider_subscription_reference(execute, reference) is None
        assert (
            await operations.load_benefit_transaction_by_source(
                execute,
                source_id=command.source_id,
                source_transaction_id=command.source_transaction_id,
            )
            is None
        )
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_stale_revoke_rolls_back_and_preserves_current_entitlements(
        self,
        package: BenefitPackageTemplate,
    ) -> None:
        current_snapshot = make_subscription_snapshot(benefit_id=package.id)
        current_grant = await _apply(current_snapshot, make_transaction_command())
        stale_snapshot = current_snapshot.replace(
            status=SubscriptionStatusId.ended,
            provider_status=ProviderStatus("canceled"),
            provider_updated_at=current_snapshot.provider_updated_at - datetime.timedelta(seconds=1),
        )
        stale_command = make_transaction_command(target=InternalTarget(internal_id=current_grant.target_id))

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(errors.StaleBenefitTransaction):
                    await _apply(stale_snapshot, stale_command)

        assert await subscription_domain.get_subscription(current_grant.target_id) == current_snapshot.with_identity(
            subscription_id=current_grant.target_id,
            state_transaction_id=current_grant.transaction_id,
        )
        current_source = await entitlement_helpers.load_source_entitlement(
            execute,
            current_snapshot.user_id,
            EntitlementKindId.day_tokens,
            current_grant.transaction_id,
        )
        assert current_source is not None
        assert current_source.revoked_at is None
        assert (
            await operations.load_benefit_transaction_by_source(
                execute,
                source_id=stale_command.source_id,
                source_transaction_id=stale_command.source_transaction_id,
            )
            is None
        )
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_new_grant_preserves_and_revokes_previous_source_grant(
        self,
        package: BenefitPackageTemplate,
    ) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)
        snapshot = make_subscription_snapshot(
            benefit_id=package.id,
            period_starts_at=now - datetime.timedelta(days=2),
            period_ends_at=now + datetime.timedelta(days=2),
        )
        first = await _apply(snapshot, make_transaction_command())
        replacement_snapshot = snapshot.replace(
            period_starts_at=now - datetime.timedelta(days=1),
            period_ends_at=now + datetime.timedelta(days=3),
            provider_updated_at=snapshot.provider_updated_at + datetime.timedelta(seconds=1),
        )
        replacement_command = make_transaction_command(
            target=InternalTarget(internal_id=first.target_id),
            effective_at=now - datetime.timedelta(days=1),
        )

        application_started_at = datetime.datetime.now(tz=datetime.UTC)
        async with TableSizeDelta("en_source_entitlements", delta=1):
            replacement = await _apply(replacement_snapshot, replacement_command)
        application_finished_at = datetime.datetime.now(tz=datetime.UTC)

        previous_source = await entitlement_helpers.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.day_tokens,
            first.transaction_id,
        )
        replacement_source = await entitlement_helpers.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.day_tokens,
            replacement.transaction_id,
        )
        assert previous_source is not None
        assert previous_source.revoked_at is not None
        assert application_started_at <= previous_source.revoked_at <= application_finished_at
        assert previous_source.revoked_by_transaction_id == replacement.transaction_id
        assert replacement_source is not None
        assert replacement_source.starts_at == replacement_snapshot.period_starts_at
        assert replacement_source.revoked_at is None

    @pytest.mark.asyncio
    async def test_revocation_failure_rolls_back_transaction_and_subscription(
        self,
        package: BenefitPackageTemplate,
        mocker: MockerFixture,
    ) -> None:
        snapshot = make_subscription_snapshot(benefit_id=package.id)
        grant = await _apply(snapshot, make_transaction_command())
        updated_snapshot = snapshot.replace(
            status=SubscriptionStatusId.ended,
            provider_status=ProviderStatus("canceled"),
            provider_updated_at=snapshot.provider_updated_at + datetime.timedelta(seconds=1),
        )
        command = make_transaction_command(target=InternalTarget(internal_id=grant.target_id))
        mocker.patch.object(
            entitlement_domain,
            "revoke_subscription_entitlements",
            side_effect=RuntimeError("entitlement revocation failed"),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(RuntimeError, match="entitlement revocation failed"):
                    await _apply(updated_snapshot, command)

        assert (
            await operations.load_benefit_transaction_by_source(
                execute,
                source_id=command.source_id,
                source_transaction_id=command.source_transaction_id,
            )
            is None
        )
        assert await subscription_domain.get_subscription(grant.target_id) == snapshot.with_identity(
            subscription_id=grant.target_id,
            state_transaction_id=grant.transaction_id,
        )
        source = await entitlement_helpers.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.day_tokens,
            grant.transaction_id,
        )
        assert source is not None
        assert source.revoked_at is None
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")


class TestApplyOneTimePurchaseTransaction:
    @pytest.mark.asyncio
    async def test_materializes_arbitrary_quantity_and_emits_events(
        self,
        purchase_package: BenefitPackageTemplate,
    ) -> None:
        purchase = make_purchase_snapshot(benefit_id=purchase_package.id)
        command = make_one_time_purchase_transaction_command()

        with capture_logs() as logs:
            async with (
                TableSizeDelta("b_transactions", delta=1),
                TableSizeDelta("otp_purchases", delta=1),
                TableSizeDelta("en_source_entitlements", delta=1),
                TableSizeDelta("en_entitlements", delta=1),
                TableSizeDelta("a_records", delta=2),
            ):
                result = await _apply_purchase(
                    purchase,
                    {_QUANTITY_PARAMETER_ID: 137},
                    command,
                )

        assert result.transaction_created
        stored_transaction = await domain.get_benefit_transaction(result.transaction_id)
        assert stored_transaction is not None
        assert stored_transaction.source_identity == command.source_identity
        assert stored_transaction.entitlement_action == BenefitEntitlementAction.grant
        assert stored_transaction.benefit_id == purchase_package.id
        assert stored_transaction.period_starts_at == purchase.purchased_at
        assert stored_transaction.period_ends_at == LIFETIME_INTERVAL_END_MARKER
        assert await purchase_domain.get_purchase(result.target_id) == purchase.with_identity(
            one_time_purchase_id=result.target_id,
            state_transaction_id=result.transaction_id,
        )

        source = await entitlement_helpers.load_source_entitlement(
            execute,
            purchase.user_id,
            EntitlementKindId.lifetime_tokens,
            result.transaction_id,
        )
        assert source is not None
        assert source.one_time_purchase_id == result.target_id
        assert source.subscription_id is None
        assert source.value == 137
        assert source.starts_at == purchase.purchased_at
        assert source.expires_at == LIFETIME_INTERVAL_END_MARKER

        assert_logs_has_business_event(
            logs,
            "one_time_purchase_changed",
            user_id=purchase.user_id,
            one_time_purchase_id=str(result.target_id),
            state_transaction_id=str(result.transaction_id),
        )
        assert_logs_has_business_event(
            logs,
            "source_entitlement_changed",
            user_id=purchase.user_id,
            one_time_purchase_id=str(result.target_id),
            grant_transaction_id=str(result.transaction_id),
        )
        assert_logs_has_business_event(logs, "entitlement_changed", user_id=purchase.user_id)
        assert sum(record.get("event") == "one_time_purchase_changed" for record in logs) == 1
        assert sum(record.get("event") == "source_entitlement_changed" for record in logs) == 1
        assert sum(record.get("event") == "entitlement_changed" for record in logs) == 1
        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    async def test_independent_additive_purchases_and_refund_only_selected_purchase(
        self,
        purchase_package: BenefitPackageTemplate,
    ) -> None:
        first_purchase = make_purchase_snapshot(benefit_id=purchase_package.id)
        second_purchase = make_purchase_snapshot(
            user_id=first_purchase.user_id,
            benefit_id=purchase_package.id,
        )
        first = await _apply_purchase(
            first_purchase,
            {_QUANTITY_PARAMETER_ID: 100},
            make_one_time_purchase_transaction_command(),
        )
        second = await _apply_purchase(
            second_purchase,
            {_QUANTITY_PARAMETER_ID: 250},
            make_one_time_purchase_transaction_command(),
        )

        effective = (
            await entitlement_domain.get_entitlements(
                [first_purchase.user_id],
                [EntitlementKindId.lifetime_tokens],
            )
        )[first_purchase.user_id][EntitlementKindId.lifetime_tokens]
        assert effective is not None
        assert effective.value == 350
        assert first.target_id != second.target_id

        refund_snapshot = first_purchase.replace(
            status=PurchaseStatus.refunded,
            provider_status=ProviderStatus("refunded"),
            provider_updated_at=first_purchase.provider_updated_at + datetime.timedelta(seconds=1),
        )
        refund = await _apply_purchase(
            refund_snapshot,
            {_QUANTITY_PARAMETER_ID: 100},
            make_one_time_purchase_transaction_command(
                target=InternalTarget(internal_id=first.target_id),
            ),
        )

        first_source = await entitlement_helpers.load_source_entitlement(
            execute,
            first_purchase.user_id,
            EntitlementKindId.lifetime_tokens,
            first.transaction_id,
        )
        second_source = await entitlement_helpers.load_source_entitlement(
            execute,
            second_purchase.user_id,
            EntitlementKindId.lifetime_tokens,
            second.transaction_id,
        )
        assert first_source is not None
        assert first_source.revoked_at is not None
        assert first_source.revoked_by_transaction_id == refund.transaction_id
        assert second_source is not None
        assert second_source.revoked_at is None

        effective = (
            await entitlement_domain.get_entitlements(
                [first_purchase.user_id],
                [EntitlementKindId.lifetime_tokens],
            )
        )[first_purchase.user_id][EntitlementKindId.lifetime_tokens]
        assert effective is not None
        assert effective.value == 250
        assert await purchase_domain.get_purchase(first.target_id) == refund_snapshot.with_identity(
            one_time_purchase_id=first.target_id,
            state_transaction_id=refund.transaction_id,
        )
        assert await purchase_domain.get_purchase(second.target_id) == second_purchase.with_identity(
            one_time_purchase_id=second.target_id,
            state_transaction_id=second.transaction_id,
        )

    @pytest.mark.asyncio
    async def test_source_retry_returns_first_result_without_rematerializing(
        self,
        purchase_package: BenefitPackageTemplate,
    ) -> None:
        first_purchase = make_purchase_snapshot(benefit_id=purchase_package.id)
        command = make_one_time_purchase_transaction_command()
        first = await _apply_purchase(
            first_purchase,
            {_QUANTITY_PARAMETER_ID: 100},
            command,
        )
        retry_purchase = make_purchase_snapshot(
            benefit_id=BenefitId("unknown"),
            status=PurchaseStatus.refunded,
        )
        retry_command = make_one_time_purchase_transaction_command(
            source_id=command.source_id,
            source_transaction_id=command.source_transaction_id,
            target=InternalTarget(internal_id=purchase_domain.new_purchase_id()),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("otp_purchases"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                retry = await _apply_purchase(retry_purchase, {}, retry_command)

        assert retry == first.replace(transaction_created=False)
        assert await purchase_domain.get_purchase(first.target_id) == first_purchase.with_identity(
            one_time_purchase_id=first.target_id,
            state_transaction_id=first.transaction_id,
        )
        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_concurrent_source_attempt_has_one_winner(
        self,
        purchase_package: BenefitPackageTemplate,
        mocker: MockerFixture,
    ) -> None:
        assert_pool_capacity_at_least(2)
        purchase = make_purchase_snapshot(benefit_id=purchase_package.id)
        command = make_one_time_purchase_transaction_command()
        original_load = operations.load_benefit_transaction_by_source
        both_initial_loads_finished = asyncio.Event()
        initial_load_count = 0

        async def synchronized_load(
            load_execute: ExecuteType,
            *,
            source_id: BenefitSourceId,
            source_transaction_id: BenefitSourceTransactionId,
        ) -> BenefitTransaction | None:
            nonlocal initial_load_count
            stored = await original_load(
                load_execute,
                source_id=source_id,
                source_transaction_id=source_transaction_id,
            )
            initial_load_count += 1
            if initial_load_count == 2:
                both_initial_loads_finished.set()
            await both_initial_loads_finished.wait()
            return stored

        mocker.patch.object(
            operations,
            "load_benefit_transaction_by_source",
            side_effect=synchronized_load,
        )

        with capture_logs() as logs:
            async with (
                TableSizeDelta("b_transactions", delta=1),
                TableSizeDelta("otp_purchases", delta=1),
                TableSizeDelta("en_source_entitlements", delta=1),
                TableSizeDelta("en_entitlements", delta=1),
                TableSizeDelta("a_records", delta=2),
            ):
                outcomes = await asyncio.gather(
                    _apply_purchase(purchase, {_QUANTITY_PARAMETER_ID: 100}, command),
                    _apply_purchase(purchase, {_QUANTITY_PARAMETER_ID: 100}, command),
                    return_exceptions=True,
                )

        successful = [outcome for outcome in outcomes if isinstance(outcome, BenefitTransactionApplicationResult)]
        failed = [outcome for outcome in outcomes if isinstance(outcome, Exception)]
        assert len(successful) == 1
        assert len(failed) == 1
        assert isinstance(failed[0], errors.ConcurrentBenefitTransaction)
        assert successful[0].transaction_created
        assert await purchase_domain.get_purchase(successful[0].target_id) == purchase.with_identity(
            one_time_purchase_id=successful[0].target_id,
            state_transaction_id=successful[0].transaction_id,
        )
        assert_logs_has_business_event(logs, "one_time_purchase_changed", user_id=purchase.user_id)
        assert_logs_has_business_event(logs, "source_entitlement_changed", user_id=purchase.user_id)
        assert_logs_has_business_event(logs, "entitlement_changed", user_id=purchase.user_id)
        assert sum(record.get("event") == "one_time_purchase_changed" for record in logs) == 1
        assert sum(record.get("event") == "source_entitlement_changed" for record in logs) == 1
        assert sum(record.get("event") == "entitlement_changed" for record in logs) == 1
        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    async def test_stale_refund_rolls_back_and_preserves_current_entitlement(
        self,
        purchase_package: BenefitPackageTemplate,
    ) -> None:
        current_purchase = make_purchase_snapshot(benefit_id=purchase_package.id)
        current = await _apply_purchase(
            current_purchase,
            {_QUANTITY_PARAMETER_ID: 100},
            make_one_time_purchase_transaction_command(),
        )
        stale_purchase = current_purchase.replace(
            status=PurchaseStatus.refunded,
            provider_status=ProviderStatus("refunded"),
            provider_updated_at=current_purchase.provider_updated_at - datetime.timedelta(seconds=1),
        )
        stale_command = make_one_time_purchase_transaction_command(
            target=InternalTarget(internal_id=current.target_id),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("otp_purchases"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(errors.StaleBenefitTransaction):
                    await _apply_purchase(
                        stale_purchase,
                        {_QUANTITY_PARAMETER_ID: 100},
                        stale_command,
                    )

        assert await purchase_domain.get_purchase(current.target_id) == current_purchase.with_identity(
            one_time_purchase_id=current.target_id,
            state_transaction_id=current.transaction_id,
        )
        source = await entitlement_helpers.load_source_entitlement(
            execute,
            current_purchase.user_id,
            EntitlementKindId.lifetime_tokens,
            current.transaction_id,
        )
        assert source is not None
        assert source.revoked_at is None
        assert (
            await operations.load_benefit_transaction_by_source(
                execute,
                source_id=stale_command.source_id,
                source_transaction_id=stale_command.source_transaction_id,
            )
            is None
        )
        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_correction_replaces_only_purchase_owned_value(
        self,
        purchase_package: BenefitPackageTemplate,
    ) -> None:
        purchase = make_purchase_snapshot(benefit_id=purchase_package.id)
        original = await _apply_purchase(
            purchase,
            {_QUANTITY_PARAMETER_ID: 500},
            make_one_time_purchase_transaction_command(),
        )
        correction_snapshot = purchase.replace(
            provider_status=ProviderStatus("paid-corrected"),
            provider_updated_at=purchase.provider_updated_at + datetime.timedelta(seconds=1),
        )
        correction_command = make_one_time_purchase_transaction_command(
            target=InternalTarget(internal_id=original.target_id),
        )

        application_started_at = datetime.datetime.now(tz=datetime.UTC)
        async with (
            TableSizeDelta("b_transactions", delta=1),
            TableSizeNotChanged("otp_purchases"),
            TableSizeDelta("en_source_entitlements", delta=1),
            TableSizeNotChanged("en_entitlements"),
            TableSizeDelta("a_records", delta=3),
        ):
            correction = await _apply_purchase(
                correction_snapshot,
                {_QUANTITY_PARAMETER_ID: 200},
                correction_command,
            )
        application_finished_at = datetime.datetime.now(tz=datetime.UTC)

        original_source = await entitlement_helpers.load_source_entitlement(
            execute,
            purchase.user_id,
            EntitlementKindId.lifetime_tokens,
            original.transaction_id,
        )
        corrected_source = await entitlement_helpers.load_source_entitlement(
            execute,
            purchase.user_id,
            EntitlementKindId.lifetime_tokens,
            correction.transaction_id,
        )
        assert original_source is not None
        assert original_source.revoked_at is not None
        assert application_started_at <= original_source.revoked_at <= application_finished_at
        assert original_source.revoked_by_transaction_id == correction.transaction_id
        assert corrected_source is not None
        assert corrected_source.value == 200
        assert corrected_source.revoked_at is None

        effective = (
            await entitlement_domain.get_entitlements(
                [purchase.user_id],
                [EntitlementKindId.lifetime_tokens],
            )
        )[purchase.user_id][EntitlementKindId.lifetime_tokens]
        assert effective is not None
        assert effective.value == 200
        assert await purchase_domain.get_purchase(original.target_id) == correction_snapshot.with_identity(
            one_time_purchase_id=original.target_id,
            state_transaction_id=correction.transaction_id,
        )

    @pytest.mark.asyncio
    async def test_entitlement_failure_rolls_back_transaction_purchase_reference_and_audit(
        self,
        purchase_package: BenefitPackageTemplate,
        mocker: MockerFixture,
    ) -> None:
        reference = make_provider_purchase_reference()
        target = make_external_target(reference)
        purchase = make_purchase_snapshot(benefit_id=purchase_package.id)
        command = make_one_time_purchase_transaction_command(target=target)
        mocker.patch.object(
            entitlement_domain,
            "grant_source_entitlements",
            side_effect=RuntimeError("entitlement write failed"),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("otp_purchase_refs"),
                TableSizeNotChanged("otp_purchases"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(RuntimeError, match="entitlement write failed"):
                    await _apply_purchase(
                        purchase,
                        {_QUANTITY_PARAMETER_ID: 100},
                        command,
                    )

        assert await purchase_domain.load_provider_purchase_reference(execute, reference) is None
        assert (
            await operations.load_benefit_transaction_by_source(
                execute,
                source_id=command.source_id,
                source_transaction_id=command.source_transaction_id,
            )
            is None
        )
        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_callback_failure_happens_after_commit(
        self,
        purchase_package: BenefitPackageTemplate,
        mocker: MockerFixture,
    ) -> None:
        purchase = make_purchase_snapshot(benefit_id=purchase_package.id)
        command = make_one_time_purchase_transaction_command()
        mocker.patch.object(
            purchase_domain,
            "_emit_purchase_change_event",
            side_effect=RuntimeError("event delivery failed"),
        )

        with capture_logs() as logs:
            async with (
                TableSizeDelta("b_transactions", delta=1),
                TableSizeDelta("otp_purchases", delta=1),
                TableSizeDelta("en_source_entitlements", delta=1),
                TableSizeDelta("en_entitlements", delta=1),
                TableSizeDelta("a_records", delta=2),
            ):
                with pytest.raises(RuntimeError, match="event delivery failed"):
                    await _apply_purchase(
                        purchase,
                        {_QUANTITY_PARAMETER_ID: 100},
                        command,
                    )

        stored_transaction = await operations.load_benefit_transaction_by_source(
            execute,
            source_id=command.source_id,
            source_transaction_id=command.source_transaction_id,
        )
        assert stored_transaction is not None
        one_time_purchase_id = stored_transaction.get_one_time_purchase_id_or_raise()
        assert await purchase_domain.get_purchase(one_time_purchase_id) == purchase.with_identity(
            one_time_purchase_id=one_time_purchase_id,
            state_transaction_id=stored_transaction.id,
        )
        source = await entitlement_helpers.load_source_entitlement(
            execute,
            purchase.user_id,
            EntitlementKindId.lifetime_tokens,
            stored_transaction.id,
        )
        assert source is not None
        assert source.one_time_purchase_id == one_time_purchase_id
        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")
        assert sum(record.get("event") == "source_entitlement_changed" for record in logs) == 1
        assert sum(record.get("event") == "entitlement_changed" for record in logs) == 1
        assert_logs_has_business_event(logs, "source_entitlement_changed", user_id=purchase.user_id)
        assert_logs_has_business_event(logs, "entitlement_changed", user_id=purchase.user_id)


class TestRunBusinessEventCallbacks:
    def test_runs_all_callbacks_in_order(self) -> None:
        calls: list[str] = []

        domain._run_business_event_callbacks(
            [
                lambda: calls.append("first"),
                lambda: calls.append("second"),
            ]
        )

        assert calls == ["first", "second"]

    def test_callback_failure__runs_remaining_callbacks_and_raises_first_error(self) -> None:
        calls: list[str] = []

        def first() -> None:
            calls.append("first")
            raise RuntimeError("first callback failed")

        def second() -> None:
            calls.append("second")
            raise ValueError("second callback failed")

        with pytest.raises(RuntimeError, match="first callback failed"):
            domain._run_business_event_callbacks([first, second, lambda: calls.append("third")])

        assert calls == ["first", "second", "third"]


class TestSubscriptionHasRequiredEntitlements:
    def test_compares_current_and_future_projection_and_ignores_expired_history(self) -> None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)
        snapshot = make_subscription_snapshot(
            period_starts_at=evaluation_time - datetime.timedelta(days=2),
            period_ends_at=evaluation_time + datetime.timedelta(days=2),
        )
        subscription_id = subscription_domain.new_subscription_id()
        matching = make_source_entitlement(
            user_id=snapshot.user_id,
            subscription_id=subscription_id,
            value=10,
            starts_at=evaluation_time - datetime.timedelta(days=1),
            expires_at=snapshot.period_ends_at,
        )
        expired = make_source_entitlement(
            user_id=snapshot.user_id,
            subscription_id=subscription_id,
            value=99,
            starts_at=evaluation_time - datetime.timedelta(days=2),
            expires_at=evaluation_time,
        )

        assert domain._subscription_has_required_entitlements(
            make_benefit_package(),
            snapshot,
            [matching, expired],
            evaluation_time=evaluation_time,
        )

    def test_detects_wrong_value_and_duplicate_grants(self) -> None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)
        snapshot = make_subscription_snapshot()
        subscription_id = subscription_domain.new_subscription_id()
        matching = make_source_entitlement(
            user_id=snapshot.user_id,
            subscription_id=subscription_id,
            value=10,
            starts_at=snapshot.period_starts_at,
            expires_at=snapshot.period_ends_at,
        )

        assert not domain._subscription_has_required_entitlements(
            make_benefit_package(),
            snapshot,
            [matching.replace(value=11)],
            evaluation_time=evaluation_time,
        )
        assert not domain._subscription_has_required_entitlements(
            make_benefit_package(),
            snapshot,
            [matching, matching.replace(grant_transaction_id=BenefitTransactionId(uuid.uuid4()))],
            evaluation_time=evaluation_time,
        )


class TestRefreshSubscriptionEntitlements:
    @staticmethod
    def command(package: BenefitPackageTemplate) -> BenefitSubscriptionRefreshCommand:
        return BenefitSubscriptionRefreshCommand(
            source_id=ADMIN_BENEFIT_SOURCE_ID,
            benefit_id=package.id,
            effective_at=datetime.datetime.now(tz=datetime.UTC),
        )

    @pytest.mark.asyncio
    async def test_no_eligible_subscriptions(self, mocker: MockerFixture) -> None:
        package = make_benefit_package_template(benefit_id=BenefitId(f"refresh-{uuid.uuid4()}"))
        mocker.patch.object(domain.settings, "package_templates", (package,))

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                results = await domain.refresh_subscription_entitlements(
                    self.command(package),
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert results == []
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_matching_entitlements_create_no_transaction(
        self,
        mocker: MockerFixture,
    ) -> None:
        package = make_benefit_package_template(benefit_id=BenefitId(f"refresh-{uuid.uuid4()}"))
        mocker.patch.object(domain.settings, "package_templates", (package,))
        snapshot = make_subscription_snapshot(benefit_id=package.id)
        applied = await _apply(snapshot, make_transaction_command())
        command = self.command(package)

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                results = await domain.refresh_subscription_entitlements(
                    command,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert results == [
            BenefitSubscriptionRefreshResult(
                subscription_id=applied.target_id,
                outcome=BenefitSubscriptionRefreshOutcome.unchanged,
            )
        ]
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_parameterized_package_is_not_supported(self, mocker: MockerFixture) -> None:
        package = make_benefit_package_template(benefit_id=BenefitId(f"refresh-{uuid.uuid4()}"))
        mocker.patch.object(domain.settings, "package_templates", (package,))
        snapshot = make_subscription_snapshot(benefit_id=package.id)
        await _apply(snapshot, make_transaction_command())
        quantity = BenefitParameterDefinition(
            id=BenefitParameterId("quantity"),
            minimum=1,
            maximum=100,
        )
        parameterized_package = make_benefit_package_template(
            benefit_id=package.id,
            parameters=(quantity,),
            entitlements={
                EntitlementKindId.month_tokens: ParameterReference(parameter_id=quantity.id),
            },
        )
        mocker.patch.object(domain.settings, "package_templates", (parameterized_package,))

        async with (
            TableSizeNotChanged("b_transactions"),
            TableSizeNotChanged("sb_subscriptions"),
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            with pytest.raises(errors.MissingBenefitParameter) as exception_info:
                await domain.refresh_subscription_entitlements(
                    self.command(parameterized_package),
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        attributes = cast(dict[str, object], vars(exception_info.value))
        assert attributes["parameter_id"] == quantity.id

    @pytest.mark.asyncio
    async def test_changed_package_replaces_entitlements_without_changing_subscription(
        self,
        mocker: MockerFixture,
    ) -> None:
        package = make_benefit_package_template(benefit_id=BenefitId(f"refresh-{uuid.uuid4()}"))
        mocker.patch.object(domain.settings, "package_templates", (package,))
        snapshot = make_subscription_snapshot(benefit_id=package.id)
        applied = await _apply(snapshot, make_transaction_command())
        replacement_package = make_benefit_package_template(
            benefit_id=package.id,
            entitlements={EntitlementKindId.day_tokens: ParameterConstant(value=20)},
        )
        mocker.patch.object(domain.settings, "package_templates", (replacement_package,))
        command = self.command(replacement_package)

        with capture_logs() as logs:
            async with (
                TableSizeDelta("b_transactions", delta=1),
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeDelta("en_source_entitlements", delta=1),
                TableSizeNotChanged("en_entitlements"),
                TableSizeDelta("a_records", delta=2),
            ):
                results = await domain.refresh_subscription_entitlements(
                    command,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert len(results) == 1
        result = results[0]
        assert result.outcome == BenefitSubscriptionRefreshOutcome.updated
        assert result.transaction_id is not None
        assert await subscription_domain.get_subscription(applied.target_id) == snapshot.with_identity(
            subscription_id=applied.target_id,
            state_transaction_id=applied.transaction_id,
        )
        previous_source = await entitlement_helpers.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.day_tokens,
            applied.transaction_id,
        )
        replacement_source = await entitlement_helpers.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.day_tokens,
            result.transaction_id,
        )
        assert previous_source is not None
        assert previous_source.revoked_by_transaction_id == result.transaction_id
        assert replacement_source is not None
        assert replacement_source.value == 20
        assert replacement_source.revoked_at is None
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert sum(record.get("event") == "source_entitlement_changed" for record in logs) == 2
        assert sum(record.get("event") == "entitlement_changed" for record in logs) == 2
        assert_logs_has_business_event(logs, "source_entitlement_changed", user_id=snapshot.user_id)
        assert_logs_has_business_event(logs, "entitlement_changed", user_id=snapshot.user_id)

        async with (
            TableSizeNotChanged("b_transactions"),
            TableSizeNotChanged("sb_subscriptions"),
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            retry = await domain.refresh_subscription_entitlements(
                command,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert retry == [
            BenefitSubscriptionRefreshResult(
                subscription_id=applied.target_id,
                outcome=BenefitSubscriptionRefreshOutcome.unchanged,
            )
        ]

    @pytest.mark.asyncio
    async def test_ended_subscription_is_not_processed(self, mocker: MockerFixture) -> None:
        package = make_benefit_package_template(benefit_id=BenefitId(f"refresh-{uuid.uuid4()}"))
        mocker.patch.object(domain.settings, "package_templates", (package,))
        snapshot = make_subscription_snapshot(
            benefit_id=package.id,
            status=SubscriptionStatusId.ended,
            provider_status="ended",
        )
        applied = await _apply(snapshot, make_transaction_command())

        async with (
            TableSizeNotChanged("b_transactions"),
            TableSizeNotChanged("sb_subscriptions"),
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            results = await domain.refresh_subscription_entitlements(
                self.command(package),
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert results == [
            BenefitSubscriptionRefreshResult(
                subscription_id=applied.target_id,
                outcome=BenefitSubscriptionRefreshOutcome.ineligible,
            )
        ]

    @pytest.mark.asyncio
    async def test_selected_subscription_disappeared(self, mocker: MockerFixture) -> None:
        package = make_benefit_package_template(benefit_id=BenefitId(f"refresh-{uuid.uuid4()}"))
        mocker.patch.object(domain.settings, "package_templates", (package,))
        candidate = make_subscription_snapshot(benefit_id=package.id).with_identity(
            subscription_id=subscription_domain.new_subscription_id(),
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
        )
        subscription_ids: list[SubscriptionId] = [candidate.id]
        mocker.patch.object(
            subscription_domain,
            "load_subscription_ids_by_benefit",
            return_value=subscription_ids,
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(errors.InvalidBenefitSubscription) as exception_info:
                    await domain.refresh_subscription_entitlements(
                        self.command(package),
                        actor_kind=_ACTOR_KIND,
                        actor_id=_ACTOR_ID,
                    )

        attributes = cast(dict[str, object], vars(exception_info.value))
        assert attributes["subscription_id"] == str(candidate.id)
        assert attributes["reason"] == "not found"
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")
