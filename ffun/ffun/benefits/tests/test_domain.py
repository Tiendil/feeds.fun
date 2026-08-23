import datetime
import uuid
from collections.abc import Callable

import pytest
from pytest_mock import MockerFixture

from ffun.audit.entities import AuditEntityKind
from ffun.benefits import domain, errors, operations
from ffun.benefits.entities import (
    BenefitEntitlementAction,
    BenefitPackageTemplate,
    BenefitParameterDefinition,
    BenefitParameterId,
    BenefitTransactionApplicationResult,
    BenefitTransactionCommand,
    InternalTarget,
    NewTarget,
    ParameterConstant,
    ParameterReference,
)
from ffun.benefits.tests.make import (
    make_benefit_package,
    make_benefit_package_template,
    make_benefit_transaction,
    make_external_target,
    make_one_time_purchase_benefit_transaction,
    make_subscription_snapshot,
    make_transaction_command,
)
from ffun.core.postgresql import execute, transaction
from ffun.core.tests.helpers import (
    TableSizeDelta,
    TableSizeNotChanged,
    assert_logs_has_business_event,
    assert_logs_has_no_business_event,
    capture_logs,
)
from ffun.domain.datetime_intervals import LIFETIME_INTERVAL_END_MARKER
from ffun.domain.entities import (
    BenefitId,
    BenefitTransactionId,
    PurchasedStateSaveOutcome,
    SerializedId,
    SubscriptionId,
)
from ffun.entitlements import domain as entitlement_domain
from ffun.entitlements.entities import EntitlementGuarantee, EntitlementKindId
from ffun.entitlements.tests import helpers as entitlement_helpers
from ffun.subscriptions import domain as subscription_domain
from ffun.subscriptions.entities import (
    SubscriptionSaveResult,
    SubscriptionSnapshot,
    SubscriptionStatusId,
)
from ffun.subscriptions.tests.make import make_provider_subscription_reference

_ACTOR_KIND = AuditEntityKind.psp
_ACTOR_ID = SerializedId("provider-hook")


@pytest.fixture  # type: ignore[misc]
def package(mocker: MockerFixture) -> BenefitPackageTemplate:
    configured = make_benefit_package_template()
    mocker.patch.object(domain.settings, "package_templates", (configured,))
    return configured


async def _apply(
    subscription: SubscriptionSnapshot,
    command: BenefitTransactionCommand[SubscriptionId],
) -> BenefitTransactionApplicationResult[SubscriptionId]:
    return await domain.apply_subscription_transaction(
        subscription,
        {},
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


class TestResolveSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_unsupported_target(self) -> None:
        with pytest.raises(NotImplementedError, match="Unsupported subscription target"):
            await domain._resolve_subscription_target(object(), execute)


class TestResolveInternalSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_internal_target_preserves_identity(self) -> None:
        subscription_id = subscription_domain.new_subscription_id()

        assert (
            await domain._resolve_subscription_target(
                InternalTarget(internal_id=subscription_id),
                execute,
            )
            == subscription_id
        )


class TestResolveExternalSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_unknown_external_target_has_no_identity(self) -> None:
        assert await domain._resolve_subscription_target(make_external_target(), execute) is None

    @pytest.mark.asyncio
    async def test_external_target_returns_stored_identity(self) -> None:
        target = make_external_target()
        subscription_id = subscription_domain.new_subscription_id()
        await subscription_domain.insert_provider_subscription_reference(
            execute,
            target.provider_reference,
            subscription_id=subscription_id,
        )

        assert await domain._resolve_subscription_target(target, execute) == subscription_id


class TestResolveNewSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_new_target_has_no_identity(self) -> None:
        assert await domain._resolve_subscription_target(NewTarget(), execute) is None


class TestResolveRegularSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_preserves_internal_identity(self) -> None:
        subscription_id = subscription_domain.new_subscription_id()

        assert (
            await domain._resolve_regular_subscription_target(
                execute,
                InternalTarget(internal_id=subscription_id),
            )
            == subscription_id
        )

    @pytest.mark.asyncio
    async def test_generates_identity_for_new_target(self) -> None:
        subscription_id = await domain._resolve_regular_subscription_target(execute, NewTarget())

        assert isinstance(subscription_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_creates_and_reuses_external_reference(self) -> None:
        target = make_external_target()

        async with TableSizeDelta("sb_subscription_refs", delta=1):
            first_id = await domain._resolve_regular_subscription_target(execute, target)

        async with TableSizeNotChanged("sb_subscription_refs"):
            second_id = await domain._resolve_regular_subscription_target(execute, target)

        assert second_id == first_id
        assert (
            await subscription_domain.load_provider_subscription_reference(execute, target.provider_reference)
            == first_id
        )


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


class TestAcceptSubscriptionTransaction:
    @pytest.mark.asyncio
    async def test_concurrent_source_save_raises_before_subscription_save(self, mocker: MockerFixture) -> None:
        benefit_transaction = make_benefit_transaction()
        save_transaction = mocker.patch.object(operations, "save_benefit_transaction", return_value=False)
        save_subscription = mocker.patch.object(subscription_domain, "save_subscription")

        with pytest.raises(errors.ConcurrentBenefitTransaction):
            await domain._accept_subscription_transaction(
                execute,
                benefit_transaction,
                make_subscription_snapshot(user_id=benefit_transaction.user_id),
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        save_transaction.assert_awaited_once_with(execute, benefit_transaction)
        save_subscription.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_persists_transaction_and_subscription(self) -> None:
        benefit_transaction = make_benefit_transaction()
        subscription_id = benefit_transaction.get_subscription_id_or_raise()
        snapshot = make_subscription_snapshot(user_id=benefit_transaction.user_id)

        async with (
            TableSizeDelta("b_transactions", delta=1),
            TableSizeDelta("sb_subscriptions", delta=1),
            transaction() as transaction_execute,
        ):
            result, callback = await domain._accept_subscription_transaction(
                transaction_execute,
                benefit_transaction,
                snapshot,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert result.outcome == PurchasedStateSaveOutcome.created
        assert callable(callback)
        assert await operations.load_benefit_transaction(execute, benefit_transaction.id) == benefit_transaction
        assert await subscription_domain.get_subscription(subscription_id) == snapshot.with_identity(
            subscription_id=subscription_id,
            state_transaction_id=benefit_transaction.id,
        )


class TestReplaceBenefit:
    @pytest.mark.asyncio
    async def test_grant_action_revokes_subscription_then_grants_package(self, mocker: MockerFixture) -> None:
        benefit_transaction = make_benefit_transaction()
        subscription_id = benefit_transaction.get_subscription_id_or_raise()
        package = make_benefit_package()
        snapshot = make_subscription_snapshot(user_id=benefit_transaction.user_id, benefit_id=package.id)
        revoke_callback = mocker.stub(name="revoke_callback")
        grant_callback = mocker.stub(name="grant_callback")
        revoke = mocker.patch.object(
            entitlement_domain,
            "revoke_subscription_entitlements",
            return_value=([], [revoke_callback]),
        )
        grant = mocker.patch.object(
            entitlement_domain,
            "grant_source_entitlements",
            return_value=([], [grant_callback]),
        )
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)

        callbacks = await domain._replace_benefit(
            execute,
            benefit_transaction,
            package,
            snapshot,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        assert callbacks == [revoke_callback, grant_callback]
        revoke.assert_awaited_once_with(
            execute,
            subscription_id=subscription_id,
            revoked_by_transaction_id=benefit_transaction.id,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )
        grant.assert_awaited_once_with(
            execute,
            source_id=domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            grant_transaction_id=benefit_transaction.id,
            user_id=benefit_transaction.user_id,
            subscription_id=subscription_id,
            one_time_purchase_id=None,
            guarantees=(EntitlementGuarantee(kind_id=EntitlementKindId.day_tokens, value=10),),
            starts_at=snapshot.period_starts_at,
            expires_at=snapshot.period_ends_at,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

    @pytest.mark.asyncio
    async def test_revoke_action_only_revokes_subscription(self, mocker: MockerFixture) -> None:
        effective_at = datetime.datetime.now(tz=datetime.UTC)
        benefit_transaction = make_benefit_transaction(
            entitlement_action=BenefitEntitlementAction.revoke,
            effective_at=effective_at,
        )
        subscription_id = benefit_transaction.get_subscription_id_or_raise()
        package = make_benefit_package()
        snapshot = make_subscription_snapshot(user_id=benefit_transaction.user_id, benefit_id=package.id)
        revoke_callback = mocker.stub(name="revoke_callback")
        revoke = mocker.patch.object(
            entitlement_domain,
            "revoke_subscription_entitlements",
            return_value=([], [revoke_callback]),
        )
        grant = mocker.patch.object(entitlement_domain, "grant_source_entitlements")
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)

        callbacks = await domain._replace_benefit(
            execute,
            benefit_transaction,
            package,
            snapshot,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        assert callbacks == [revoke_callback]
        revoke.assert_awaited_once_with(
            execute,
            subscription_id=subscription_id,
            revoked_by_transaction_id=benefit_transaction.id,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )
        grant.assert_not_awaited()


class TestApplyTransaction:
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
        mocker.patch.object(domain, "_resolve_regular_subscription_target", return_value=subscription_id)
        mocker.patch.object(operations, "new_benefit_transaction_id", return_value=transaction_id)
        mocker.patch.object(
            domain,
            "_accept_subscription_transaction",
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

        benefit_transaction, callbacks = await domain._apply_transaction(
            command,
            execute,
            snapshot,
            {},
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
        mocker.patch.object(domain, "_resolve_regular_subscription_target", return_value=subscription_id)
        mocker.patch.object(operations, "new_benefit_transaction_id", return_value=transaction_id)
        mocker.patch.object(
            domain,
            "_accept_subscription_transaction",
            return_value=(
                SubscriptionSaveResult(outcome=PurchasedStateSaveOutcome.stale, current=current),
                mocker.stub(name="subscription_callback"),
            ),
        )
        replace = mocker.patch.object(domain, "_replace_benefit")

        with pytest.raises(errors.StaleBenefitTransaction) as exception_info:
            await domain._apply_transaction(
                command,
                execute,
                snapshot,
                {},
                evaluation_time=datetime.datetime.now(tz=datetime.UTC),
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        message = str(exception_info.value)
        assert f"subscription_id={subscription_id}" in message
        assert f"incoming_provider_updated_at={snapshot.provider_updated_at.isoformat()}" in message
        assert f"current_provider_updated_at={current.provider_updated_at.isoformat()}" in message
        replace.assert_not_awaited()


class TestApplySubscriptionTransaction:
    @pytest.mark.asyncio
    async def test_grant_persists_atomic_state_and_emits_events(self, mocker: MockerFixture) -> None:
        package = make_benefit_package_template(
            entitlements={
                EntitlementKindId.day_tokens: ParameterConstant(value=10),
                EntitlementKindId.lifetime_tokens: ParameterConstant(value=100),
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
            domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            result.transaction_id,
        )
        lifetime_source = await entitlement_helpers.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.lifetime_tokens,
            domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            result.transaction_id,
        )
        assert day_source is not None
        assert day_source.subscription_id == result.target_id
        assert day_source.value == 10
        assert day_source.starts_at == snapshot.period_starts_at
        assert day_source.expires_at == snapshot.period_ends_at
        assert lifetime_source is not None
        assert lifetime_source.value == 100
        assert lifetime_source.starts_at == snapshot.period_starts_at
        assert lifetime_source.expires_at == LIFETIME_INTERVAL_END_MARKER

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
            source_id=domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            grant_transaction_id=str(result.transaction_id),
        )
        assert_logs_has_business_event(logs, "entitlement_changed", user_id=snapshot.user_id)

    @pytest.mark.asyncio
    async def test_materializes_parameterized_template(self, mocker: MockerFixture) -> None:
        quantity = BenefitParameterDefinition(
            id=BenefitParameterId("quantity"),
            minimum=1,
            maximum=100,
        )
        package = make_benefit_package_template(
            parameters=(quantity,),
            entitlements={
                EntitlementKindId.lifetime_tokens: ParameterReference(parameter_id=quantity.id),
            },
        )
        mocker.patch.object(domain.settings, "package_templates", (package,))
        snapshot = make_subscription_snapshot(benefit_id=package.id)
        command = make_transaction_command()

        async with (
            TableSizeDelta("b_transactions", delta=1),
            TableSizeDelta("sb_subscriptions", delta=1),
            TableSizeDelta("en_source_entitlements", delta=1),
            TableSizeDelta("en_entitlements", delta=1),
            TableSizeDelta("a_records", delta=2),
        ):
            result = await domain.apply_subscription_transaction(
                snapshot,
                {quantity.id: 25},
                command,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        source = await entitlement_helpers.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.lifetime_tokens,
            domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            result.transaction_id,
        )
        assert source is not None
        assert source.value == 25

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
            entitlements={EntitlementKindId.lifetime_tokens: ParameterConstant(value=30)},
        )
        mocker.patch.object(domain.settings, "package_templates", (original_package, current_package))
        original_snapshot = make_subscription_snapshot(benefit_id=original_package.id)
        grant = await _apply(original_snapshot, make_transaction_command())
        application_started_at = datetime.datetime.now(tz=datetime.UTC)
        transaction_effective_at = application_started_at - datetime.timedelta(days=1)
        current_snapshot = original_snapshot.replace(
            benefit_id=current_package.id,
            status=SubscriptionStatusId.ended,
            provider_status="canceled",
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
                domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
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
                EntitlementKindId.lifetime_tokens,
                domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
                revocation.transaction_id,
            )
            is None
        )
        assert_logs_has_business_event(logs, "subscription_changed", user_id=original_snapshot.user_id)
        assert sum(record.get("event") == "source_entitlement_changed" for record in logs) == 2
        assert sum(record.get("event") == "entitlement_changed" for record in logs) == 2

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
        mocker.patch.object(operations, "save_benefit_transaction", return_value=False)

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
            provider_status="canceled",
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
            domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
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
            domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            first.transaction_id,
        )
        replacement_source = await entitlement_helpers.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.day_tokens,
            domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
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
            provider_status="canceled",
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
            domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            grant.transaction_id,
        )
        assert source is not None
        assert source.revoked_at is None
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")
