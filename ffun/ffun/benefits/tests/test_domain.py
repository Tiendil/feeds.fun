import datetime
import uuid
from collections.abc import Callable

import pytest
from pytest_mock import MockerFixture

from ffun.audit.entities import AuditEntityKind
from ffun.benefits import domain, errors, operations
from ffun.benefits.entities import (
    BenefitPackage,
    BenefitTransactionApplicationResult,
    BenefitTransactionCommand,
    BenefitTransactionKind,
    InternalSubscriptionTarget,
    NewSubscriptionTarget,
)
from ffun.benefits.tests.make import (
    make_benefit_package,
    make_benefit_transaction,
    make_external_subscription_target,
    make_grant_command,
    make_provider_subscription_reference,
    make_revoke_command,
    make_subscription_snapshot,
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
from ffun.domain.domain import new_user_id
from ffun.domain.entities import BenefitId, BenefitTransactionId, SerializedId
from ffun.entitlements import domain as entitlement_domain
from ffun.entitlements import operations as entitlement_operations
from ffun.entitlements.entities import EntitlementGuarantee, EntitlementKindId
from ffun.subscriptions import domain as subscription_domain
from ffun.subscriptions.entities import SubscriptionSnapshot, SubscriptionStatusId

_ACTOR_KIND = AuditEntityKind.psp
_ACTOR_ID = SerializedId("provider-hook")


@pytest.fixture  # type: ignore[misc]
def package(mocker: MockerFixture) -> BenefitPackage:
    configured = make_benefit_package()
    mocker.patch.object(domain.settings, "packages", (configured,))
    return configured


async def _apply(
    subscription: SubscriptionSnapshot,
    command: BenefitTransactionCommand,
) -> BenefitTransactionApplicationResult:
    return await domain.apply_subscription_transaction(
        subscription,
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
        await operations.insert_benefit_transaction(execute, benefit_transaction)

        assert await domain.get_benefit_transaction(benefit_transaction.id) == benefit_transaction


class TestGetBenefit:
    def test_returns_configured_package(self, package: BenefitPackage) -> None:
        assert domain.get_benefit(package.id) == package

    def test_unknown_identifier_raises_module_error(self, package: BenefitPackage) -> None:
        with pytest.raises(errors.UnknownBenefit) as exception_info:
            domain.get_benefit(BenefitId("unknown"))

        assert "benefit_id=unknown" in str(exception_info.value)


class TestResolveSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_unsupported_target(self) -> None:
        with pytest.raises(NotImplementedError, match="Unsupported subscription target"):
            await domain._resolve_subscription_target(object(), execute)


class TestResolveInternalSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_returns_internal_identity(self) -> None:
        subscription_id = subscription_domain.new_subscription_id()

        assert (
            await domain._resolve_subscription_target(
                InternalSubscriptionTarget(subscription_id=subscription_id),
                execute,
            )
            == subscription_id
        )


class TestResolveExternalSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_missing_reference(self) -> None:
        target = make_external_subscription_target()

        assert await domain._resolve_subscription_target(target, execute) is None

    @pytest.mark.asyncio
    async def test_returns_stored_reference(self) -> None:
        target = make_external_subscription_target()
        subscription_id = subscription_domain.new_subscription_id()
        await operations.insert_provider_subscription_reference(
            execute,
            target.provider_reference,
            subscription_id=subscription_id,
        )

        assert await domain._resolve_subscription_target(target, execute) == subscription_id


class TestResolveNewSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_has_no_resolved_identity(self) -> None:
        assert await domain._resolve_subscription_target(NewSubscriptionTarget(), execute) is None


class TestResolveRegularSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_preserves_internal_identity(self) -> None:
        subscription_id = subscription_domain.new_subscription_id()

        assert (
            await domain._resolve_regular_subscription_target(
                execute,
                InternalSubscriptionTarget(subscription_id=subscription_id),
            )
            == subscription_id
        )

    @pytest.mark.asyncio
    async def test_generates_identity_for_new_target(self) -> None:
        subscription_id = await domain._resolve_regular_subscription_target(execute, NewSubscriptionTarget())

        assert isinstance(subscription_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_creates_external_reference(self) -> None:
        target = make_external_subscription_target()

        async with TableSizeDelta("b_subscription_refs", delta=1):
            subscription_id = await domain._resolve_regular_subscription_target(execute, target)

        assert (
            await operations.load_provider_subscription_reference(execute, target.provider_reference)
            == subscription_id
        )

    @pytest.mark.asyncio
    async def test_reuses_external_reference(self) -> None:
        target = make_external_subscription_target()
        first_id = await domain._resolve_regular_subscription_target(execute, target)

        async with TableSizeNotChanged("b_subscription_refs"):
            second_id = await domain._resolve_regular_subscription_target(execute, target)

        assert second_id == first_id


class TestLoadGrantToRevoke:
    @pytest.mark.asyncio
    async def test_missing_transaction(self) -> None:
        grant_transaction_id = BenefitTransactionId(uuid.uuid4())

        with pytest.raises(errors.BenefitTransactionNotFound):
            await domain._load_grant_to_revoke(execute, grant_transaction_id, make_subscription_snapshot())

    @pytest.mark.asyncio
    async def test_rejects_non_grant_transaction(self) -> None:
        grant = make_benefit_transaction()
        revocation = make_benefit_transaction(
            kind=BenefitTransactionKind.revoke,
            user_id=grant.user_id,
            subscription_id=grant.subscription_id,
            revokes_transaction_id=grant.id,
        )
        await operations.insert_benefit_transaction(execute, grant)
        await operations.insert_benefit_transaction(execute, revocation)

        with pytest.raises(errors.InvalidBenefitRevocation, match="Only a benefit grant"):
            await domain._load_grant_to_revoke(
                execute,
                revocation.id,
                make_subscription_snapshot(user_id=grant.user_id),
            )

    @pytest.mark.asyncio
    async def test_rejects_another_user(self) -> None:
        grant = make_benefit_transaction()
        await operations.insert_benefit_transaction(execute, grant)

        with pytest.raises(errors.InvalidBenefitRevocation, match="belongs to another subscription"):
            await domain._load_grant_to_revoke(
                execute,
                grant.id,
                make_subscription_snapshot(user_id=new_user_id()),
            )

    @pytest.mark.asyncio
    async def test_returns_matching_grant(self) -> None:
        grant = make_benefit_transaction()
        await operations.insert_benefit_transaction(execute, grant)

        assert (
            await domain._load_grant_to_revoke(
                execute,
                grant.id,
                make_subscription_snapshot(user_id=grant.user_id),
            )
            == grant
        )


class TestResolveRevokeSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_rejects_new_target(self) -> None:
        grant = make_benefit_transaction()

        with pytest.raises(errors.InvalidBenefitRevocation, match="must target an existing subscription"):
            await domain._resolve_revoke_subscription_target(execute, NewSubscriptionTarget(), grant)

    @pytest.mark.asyncio
    async def test_rejects_unknown_external_target(self) -> None:
        grant = make_benefit_transaction()

        with pytest.raises(errors.InvalidBenefitRevocation, match="must target an existing subscription"):
            await domain._resolve_revoke_subscription_target(
                execute,
                make_external_subscription_target(),
                grant,
            )

    @pytest.mark.asyncio
    async def test_rejects_different_internal_subscription(self) -> None:
        grant = make_benefit_transaction()

        with pytest.raises(errors.InvalidBenefitSubscription, match="targets another subscription"):
            await domain._resolve_revoke_subscription_target(
                execute,
                InternalSubscriptionTarget(subscription_id=subscription_domain.new_subscription_id()),
                grant,
            )

    @pytest.mark.asyncio
    async def test_returns_matching_internal_subscription(self) -> None:
        grant = make_benefit_transaction()

        assert (
            await domain._resolve_revoke_subscription_target(
                execute,
                InternalSubscriptionTarget(subscription_id=grant.subscription_id),
                grant,
            )
            == grant.subscription_id
        )

    @pytest.mark.asyncio
    async def test_returns_matching_external_subscription(self) -> None:
        grant = make_benefit_transaction()
        target = make_external_subscription_target()
        await operations.insert_provider_subscription_reference(
            execute,
            target.provider_reference,
            subscription_id=grant.subscription_id,
        )

        assert await domain._resolve_revoke_subscription_target(execute, target, grant) == grant.subscription_id


class TestApplicationResult:
    def test_shapes_public_result(self) -> None:
        benefit_transaction = make_benefit_transaction()

        assert domain._application_result(benefit_transaction, created=True) == BenefitTransactionApplicationResult(
            transaction_id=benefit_transaction.id,
            transaction_created=True,
            subscription_id=benefit_transaction.subscription_id,
        )


class TestAcceptSubscriptionTransaction:
    @pytest.mark.asyncio
    async def test_concurrent_source_insert_raises_before_subscription_save(self, mocker: MockerFixture) -> None:
        benefit_transaction = make_benefit_transaction()
        insert = mocker.patch.object(operations, "insert_benefit_transaction", return_value=False)
        save = mocker.patch.object(subscription_domain, "save_subscription")

        with pytest.raises(errors.ConcurrentBenefitTransaction):
            await domain._accept_subscription_transaction(
                execute,
                benefit_transaction,
                make_subscription_snapshot(user_id=benefit_transaction.user_id),
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        insert.assert_awaited_once_with(execute, benefit_transaction)
        save.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_persists_transaction_and_subscription(self) -> None:
        benefit_transaction = make_benefit_transaction()
        snapshot = make_subscription_snapshot(user_id=benefit_transaction.user_id)

        async with transaction() as transaction_execute:
            callback = await domain._accept_subscription_transaction(
                transaction_execute,
                benefit_transaction,
                snapshot,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert callable(callback)
        assert await operations.load_benefit_transaction(execute, benefit_transaction.id) == benefit_transaction
        assert await subscription_domain.get_subscription(
            benefit_transaction.subscription_id
        ) == snapshot.with_identity(
            subscription_id=benefit_transaction.subscription_id,
            state_transaction_id=benefit_transaction.id,
        )


class TestRevokeBenefit:
    @pytest.mark.asyncio
    async def test_delegates_original_grant_and_package_kinds(self, mocker: MockerFixture) -> None:
        grant = make_benefit_transaction()
        revocation = make_benefit_transaction(
            kind=BenefitTransactionKind.revoke,
            user_id=grant.user_id,
            subscription_id=grant.subscription_id,
            revokes_transaction_id=grant.id,
        )
        package = make_benefit_package(
            entitlements=(
                EntitlementGuarantee(kind_id=EntitlementKindId.month_tokens, value=20),
                EntitlementGuarantee(kind_id=EntitlementKindId.day_tokens, value=10),
            )
        )
        callback = mocker.stub(name="entitlement_callback")
        revoke = mocker.patch.object(
            entitlement_domain,
            "revoke_source_entitlements",
            return_value=([], [callback]),
        )
        now = datetime.datetime.now(tz=datetime.UTC)

        callbacks = await domain._revoke_benefit(
            execute,
            revocation,
            grant,
            package,
            revoked_at=now,
            evaluation_time=now,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        assert callbacks == [callback]
        kind_ids: list[EntitlementKindId] = [
            EntitlementKindId.month_tokens,
            EntitlementKindId.day_tokens,
        ]
        revoke.assert_awaited_once_with(
            execute,
            source_id=domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            grant_transaction_id=grant.id,
            revoked_by_transaction_id=revocation.id,
            user_id=grant.user_id,
            kind_ids=kind_ids,
            revoked_at=now,
            evaluation_time=now,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )


class TestReplaceBenefit:
    @pytest.mark.asyncio
    async def test_revokes_subscription_then_grants_package(self, mocker: MockerFixture) -> None:
        benefit_transaction = make_benefit_transaction()
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
            subscription_id=benefit_transaction.subscription_id,
            revoked_by_transaction_id=benefit_transaction.id,
            revoked_at=snapshot.period_starts_at,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )
        grant.assert_awaited_once_with(
            execute,
            source_id=domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            grant_transaction_id=benefit_transaction.id,
            user_id=benefit_transaction.user_id,
            subscription_id=benefit_transaction.subscription_id,
            guarantees=package.entitlements,
            starts_at=snapshot.period_starts_at,
            expires_at=snapshot.period_ends_at,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )


class TestApplyTransactionCommand:
    @pytest.mark.asyncio
    async def test_unsupported_command(self) -> None:
        with pytest.raises(NotImplementedError, match="Unsupported benefit transaction command"):
            await domain._apply_transaction_command(
                object(),
                execute,
                make_subscription_snapshot(),
                evaluation_time=datetime.datetime.now(tz=datetime.UTC),
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )


class TestApplyGrantTransaction:
    @pytest.mark.asyncio
    async def test_builds_transaction_and_combines_callbacks(
        self,
        package: BenefitPackage,
        mocker: MockerFixture,
    ) -> None:
        snapshot = make_subscription_snapshot(benefit_id=package.id)
        command = make_grant_command()
        subscription_id = subscription_domain.new_subscription_id()
        transaction_id = BenefitTransactionId(uuid.uuid4())
        subscription_callback: Callable[[], None] = mocker.stub(name="subscription_callback")
        entitlement_callback: Callable[[], None] = mocker.stub(name="entitlement_callback")
        mocker.patch.object(
            domain,
            "_resolve_regular_subscription_target",
            return_value=subscription_id,
        )
        mocker.patch.object(operations, "new_benefit_transaction_id", return_value=transaction_id)
        mocker.patch.object(
            domain,
            "_accept_subscription_transaction",
            return_value=subscription_callback,
        )
        entitlement_callbacks: list[Callable[[], None]] = [entitlement_callback]
        mocker.patch.object(domain, "_replace_benefit", return_value=entitlement_callbacks)

        benefit_transaction, callbacks = await domain._apply_grant_transaction(
            command,
            execute,
            snapshot,
            evaluation_time=datetime.datetime.now(tz=datetime.UTC),
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        assert benefit_transaction == make_benefit_transaction(
            transaction_id=transaction_id,
            source_id=command.source_id,
            source_transaction_id=command.source_transaction_id,
            user_id=snapshot.user_id,
            benefit_id=package.id,
            subscription_id=subscription_id,
            effective_at=command.effective_at,
            period_starts_at=snapshot.period_starts_at,
            period_ends_at=snapshot.period_ends_at,
        )
        assert callbacks == [subscription_callback, entitlement_callback]


class TestApplyRevokeTransaction:
    @pytest.mark.asyncio
    async def test_records_original_grant_package_and_combines_callbacks(
        self,
        mocker: MockerFixture,
    ) -> None:
        original_package = make_benefit_package(benefit_id=BenefitId("original"))
        current_package = make_benefit_package(benefit_id=BenefitId("current"), entitlements=())
        mocker.patch.object(domain.settings, "packages", (original_package, current_package))
        grant = make_benefit_transaction(benefit_id=original_package.id)
        snapshot = make_subscription_snapshot(user_id=grant.user_id, benefit_id=current_package.id)
        command = make_revoke_command(
            subscription_target=InternalSubscriptionTarget(subscription_id=grant.subscription_id),
            revokes_transaction_id=grant.id,
        )
        transaction_id = BenefitTransactionId(uuid.uuid4())
        subscription_callback: Callable[[], None] = mocker.stub(name="subscription_callback")
        entitlement_callback: Callable[[], None] = mocker.stub(name="entitlement_callback")
        mocker.patch.object(domain, "_load_grant_to_revoke", return_value=grant)
        mocker.patch.object(
            domain,
            "_resolve_revoke_subscription_target",
            return_value=grant.subscription_id,
        )
        mocker.patch.object(operations, "new_benefit_transaction_id", return_value=transaction_id)
        mocker.patch.object(
            domain,
            "_accept_subscription_transaction",
            return_value=subscription_callback,
        )
        entitlement_callbacks: list[Callable[[], None]] = [entitlement_callback]
        revoke = mocker.patch.object(domain, "_revoke_benefit", return_value=entitlement_callbacks)

        evaluation_time = datetime.datetime.now(tz=datetime.UTC)

        benefit_transaction, callbacks = await domain._apply_revoke_transaction(
            command,
            execute,
            snapshot,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        assert benefit_transaction == make_benefit_transaction(
            transaction_id=transaction_id,
            source_id=command.source_id,
            source_transaction_id=command.source_transaction_id,
            kind=BenefitTransactionKind.revoke,
            user_id=snapshot.user_id,
            benefit_id=original_package.id,
            subscription_id=grant.subscription_id,
            effective_at=command.effective_at,
            revokes_transaction_id=grant.id,
        )
        assert callbacks == [subscription_callback, entitlement_callback]
        revoke.assert_awaited_once_with(
            execute,
            benefit_transaction,
            grant,
            original_package,
            revoked_at=benefit_transaction.effective_at,
            evaluation_time=evaluation_time,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )


class TestApplySubscriptionTransaction:
    @pytest.mark.asyncio
    async def test_grant_persists_atomic_state_and_emits_events(self, mocker: MockerFixture) -> None:
        package = make_benefit_package(
            entitlements=(
                EntitlementGuarantee(kind_id=EntitlementKindId.day_tokens, value=10),
                EntitlementGuarantee(kind_id=EntitlementKindId.lifetime_tokens, value=100),
            )
        )
        mocker.patch.object(domain.settings, "packages", (package,))
        snapshot = make_subscription_snapshot(benefit_id=package.id)
        command = make_grant_command()

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
        assert stored_transaction.kind == BenefitTransactionKind.grant
        assert stored_transaction.benefit_id == package.id
        assert stored_transaction.period_starts_at == snapshot.period_starts_at
        assert stored_transaction.period_ends_at == snapshot.period_ends_at
        assert await subscription_domain.get_subscription(result.subscription_id) == snapshot.with_identity(
            subscription_id=result.subscription_id,
            state_transaction_id=result.transaction_id,
        )

        day_source = await entitlement_operations.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.day_tokens,
            domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            result.transaction_id,
        )
        lifetime_source = await entitlement_operations.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.lifetime_tokens,
            domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            result.transaction_id,
        )
        assert day_source is not None
        assert day_source.subscription_id == result.subscription_id
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
            subscription_id=str(result.subscription_id),
            state_transaction_id=str(result.transaction_id),
        )
        assert_logs_has_business_event(
            logs,
            "source_entitlement_changed",
            user_id=snapshot.user_id,
            source_id=domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            grant_transaction_id=str(result.transaction_id),
        )
        assert_logs_has_business_event(
            logs,
            "entitlement_changed",
            user_id=snapshot.user_id,
        )
        assert sum(record.get("event") == "subscription_changed" for record in logs) == 1
        assert sum(record.get("event") == "source_entitlement_changed" for record in logs) == 2
        assert sum(record.get("event") == "entitlement_changed" for record in logs) == 2

    @pytest.mark.asyncio
    async def test_empty_package_changes_no_entitlement_state(self, mocker: MockerFixture) -> None:
        package = make_benefit_package(entitlements=())
        mocker.patch.object(domain.settings, "packages", (package,))
        snapshot = make_subscription_snapshot(benefit_id=package.id)

        with capture_logs() as logs:
            async with (
                TableSizeDelta("b_transactions", delta=1),
                TableSizeDelta("sb_subscriptions", delta=1),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeDelta("a_records", delta=1),
            ):
                result = await _apply(snapshot, make_grant_command())

        assert result.transaction_created
        assert_logs_has_business_event(logs, "subscription_changed", user_id=snapshot.user_id)
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_external_target_creates_and_reuses_reference(self, mocker: MockerFixture) -> None:
        package = make_benefit_package(entitlements=())
        mocker.patch.object(domain.settings, "packages", (package,))
        target = make_external_subscription_target()
        first_snapshot = make_subscription_snapshot(benefit_id=package.id)
        second_snapshot = first_snapshot.replace(
            provider_updated_at=first_snapshot.provider_updated_at + datetime.timedelta(seconds=1)
        )

        async with TableSizeDelta("b_subscription_refs", delta=1):
            first = await _apply(
                first_snapshot,
                make_grant_command(subscription_target=target),
            )

        async with TableSizeNotChanged("b_subscription_refs"):
            second = await _apply(
                second_snapshot,
                make_grant_command(subscription_target=target),
            )

        assert second.subscription_id == first.subscription_id
        assert (
            await operations.load_provider_subscription_reference(execute, target.provider_reference)
            == first.subscription_id
        )

    @pytest.mark.asyncio
    async def test_source_retry_returns_first_result_and_ignores_new_payload(
        self,
        package: BenefitPackage,
    ) -> None:
        first_snapshot = make_subscription_snapshot(benefit_id=package.id)
        command = make_grant_command()
        first = await _apply(first_snapshot, command)
        retry_snapshot = make_subscription_snapshot(benefit_id=BenefitId("unknown"))
        retry_command = make_grant_command(
            source_id=command.source_id,
            source_transaction_id=command.source_transaction_id,
            subscription_target=InternalSubscriptionTarget(subscription_id=subscription_domain.new_subscription_id()),
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
        assert await subscription_domain.get_subscription(first.subscription_id) == first_snapshot.with_identity(
            subscription_id=first.subscription_id,
            state_transaction_id=first.transaction_id,
        )
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_unknown_benefit_rolls_back_all_state(self, package: BenefitPackage) -> None:
        reference = make_provider_subscription_reference()
        target = make_external_subscription_target(reference)
        snapshot = make_subscription_snapshot(benefit_id=BenefitId("unknown"))

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("b_subscription_refs"),
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(errors.UnknownBenefit):
                    await _apply(snapshot, make_grant_command(subscription_target=target))

        assert await operations.load_provider_subscription_reference(execute, reference) is None
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_concurrent_source_loser_rolls_back_external_reference(
        self,
        package: BenefitPackage,
        mocker: MockerFixture,
    ) -> None:
        reference = make_provider_subscription_reference()
        target = make_external_subscription_target(reference)
        mocker.patch.object(operations, "insert_benefit_transaction", return_value=False)

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("b_subscription_refs"),
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(errors.ConcurrentBenefitTransaction):
                    await _apply(
                        make_subscription_snapshot(benefit_id=package.id),
                        make_grant_command(subscription_target=target),
                    )

        assert await operations.load_provider_subscription_reference(execute, reference) is None
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_entitlement_failure_rolls_back_transaction_subscription_reference_and_audit(
        self,
        package: BenefitPackage,
        mocker: MockerFixture,
    ) -> None:
        reference = make_provider_subscription_reference()
        target = make_external_subscription_target(reference)
        command = make_grant_command(subscription_target=target)
        mocker.patch.object(
            entitlement_domain,
            "grant_source_entitlements",
            side_effect=RuntimeError("entitlement write failed"),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("b_subscription_refs"),
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(RuntimeError, match="entitlement write failed"):
                    await _apply(make_subscription_snapshot(benefit_id=package.id), command)

        assert await operations.load_provider_subscription_reference(execute, reference) is None
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
    async def test_new_grant_preserves_and_revokes_previous_source_grant(
        self,
        package: BenefitPackage,
    ) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)
        snapshot = make_subscription_snapshot(
            benefit_id=package.id,
            period_starts_at=now - datetime.timedelta(days=2),
            period_ends_at=now + datetime.timedelta(days=2),
        )
        first = await _apply(snapshot, make_grant_command())
        replacement_snapshot = snapshot.replace(
            period_starts_at=now,
            period_ends_at=now + datetime.timedelta(days=3),
            provider_updated_at=snapshot.provider_updated_at + datetime.timedelta(seconds=1)
        )

        async with TableSizeDelta("en_source_entitlements", delta=1):
            replacement = await _apply(
                replacement_snapshot,
                make_grant_command(
                    subscription_target=InternalSubscriptionTarget(subscription_id=first.subscription_id),
                ),
            )

        previous_source = await entitlement_operations.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.day_tokens,
            domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            first.transaction_id,
        )
        replacement_source = await entitlement_operations.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.day_tokens,
            domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            replacement.transaction_id,
        )
        assert previous_source is not None
        assert previous_source.revoked_at == replacement_snapshot.period_starts_at
        assert previous_source.revoked_by_transaction_id == replacement.transaction_id
        assert replacement_source is not None
        assert replacement_source.revoked_at is None
        assert replacement_source.starts_at == replacement_snapshot.period_starts_at

    @pytest.mark.asyncio
    async def test_new_grant_revokes_scheduled_future_source_grant(
        self,
        package: BenefitPackage,
    ) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)
        scheduled_snapshot = make_subscription_snapshot(
            benefit_id=package.id,
            period_starts_at=now + datetime.timedelta(days=1),
            period_ends_at=now + datetime.timedelta(days=2),
        )
        scheduled = await _apply(scheduled_snapshot, make_grant_command())
        replacement_snapshot = scheduled_snapshot.replace(
            period_starts_at=now,
            period_ends_at=now + datetime.timedelta(days=3),
            provider_updated_at=scheduled_snapshot.provider_updated_at + datetime.timedelta(seconds=1),
        )
        replacement = await _apply(
            replacement_snapshot,
            make_grant_command(
                subscription_target=InternalSubscriptionTarget(subscription_id=scheduled.subscription_id),
            ),
        )

        scheduled_source = await entitlement_operations.load_source_entitlement(
            execute,
            scheduled_snapshot.user_id,
            EntitlementKindId.day_tokens,
            domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            scheduled.transaction_id,
        )

        assert scheduled_source is not None
        assert scheduled_source.revoked_at == replacement_snapshot.period_starts_at
        assert scheduled_source.revoked_by_transaction_id == replacement.transaction_id

    @pytest.mark.asyncio
    async def test_revocation_uses_original_package_and_updates_subscription(
        self,
        mocker: MockerFixture,
    ) -> None:
        original_package = make_benefit_package(
            benefit_id=BenefitId("original"),
            entitlements=(
                EntitlementGuarantee(kind_id=EntitlementKindId.day_tokens, value=10),
                EntitlementGuarantee(kind_id=EntitlementKindId.month_tokens, value=20),
            ),
        )
        current_package = make_benefit_package(
            benefit_id=BenefitId("current"),
            entitlements=(EntitlementGuarantee(kind_id=EntitlementKindId.lifetime_tokens, value=30),),
        )
        mocker.patch.object(domain.settings, "packages", (original_package, current_package))
        original_snapshot = make_subscription_snapshot(benefit_id=original_package.id)
        grant = await _apply(original_snapshot, make_grant_command())
        revoked_at = datetime.datetime.now(tz=datetime.UTC)
        current_snapshot = original_snapshot.replace(
            benefit_id=current_package.id,
            status=SubscriptionStatusId.ended,
            provider_status="canceled",
            ends_at=revoked_at,
            provider_updated_at=original_snapshot.provider_updated_at + datetime.timedelta(seconds=1),
        )
        command = make_revoke_command(
            subscription_target=InternalSubscriptionTarget(subscription_id=grant.subscription_id),
            revokes_transaction_id=grant.transaction_id,
            effective_at=revoked_at,
        )

        with capture_logs() as logs:
            async with (
                TableSizeDelta("b_transactions", delta=1),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeDelta("a_records", delta=3),
            ):
                revocation = await _apply(current_snapshot, command)

        stored = await domain.get_benefit_transaction(revocation.transaction_id)
        assert stored is not None
        assert stored.kind == BenefitTransactionKind.revoke
        assert stored.benefit_id == original_package.id
        assert stored.revokes_transaction_id == grant.transaction_id
        assert await subscription_domain.get_subscription(grant.subscription_id) == current_snapshot.with_identity(
            subscription_id=grant.subscription_id,
            state_transaction_id=revocation.transaction_id,
        )

        for guarantee in original_package.entitlements:
            source = await entitlement_operations.load_source_entitlement(
                execute,
                original_snapshot.user_id,
                guarantee.kind_id,
                domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
                grant.transaction_id,
            )
            assert source is not None
            assert source.revoked_at == revoked_at
            assert source.revoked_by_transaction_id == revocation.transaction_id

        assert (
            await entitlement_operations.load_source_entitlement(
                execute,
                original_snapshot.user_id,
                EntitlementKindId.lifetime_tokens,
                domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
                grant.transaction_id,
            )
            is None
        )
        assert_logs_has_business_event(logs, "subscription_changed", user_id=original_snapshot.user_id)
        assert sum(record.get("event") == "source_entitlement_changed" for record in logs) == 2
        assert sum(record.get("event") == "entitlement_changed" for record in logs) == 2

    @pytest.mark.asyncio
    async def test_stale_subscription_snapshot_still_applies_revocation(
        self,
        package: BenefitPackage,
    ) -> None:
        snapshot = make_subscription_snapshot(benefit_id=package.id)
        grant = await _apply(snapshot, make_grant_command())
        stale_snapshot = snapshot.replace(
            status=SubscriptionStatusId.ended,
            provider_status="canceled",
            provider_updated_at=snapshot.provider_updated_at - datetime.timedelta(seconds=1),
        )
        revoked_at = datetime.datetime.now(tz=datetime.UTC)

        revocation = await _apply(
            stale_snapshot,
            make_revoke_command(
                subscription_target=InternalSubscriptionTarget(subscription_id=grant.subscription_id),
                revokes_transaction_id=grant.transaction_id,
                effective_at=revoked_at,
            ),
        )

        assert await subscription_domain.get_subscription(grant.subscription_id) == snapshot.with_identity(
            subscription_id=grant.subscription_id,
            state_transaction_id=grant.transaction_id,
        )
        source = await entitlement_operations.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.day_tokens,
            domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            grant.transaction_id,
        )
        assert source is not None
        assert source.revoked_at == revoked_at
        assert source.revoked_by_transaction_id == revocation.transaction_id

    @pytest.mark.asyncio
    async def test_later_revocation_preserves_earliest_revocation_state(
        self,
        package: BenefitPackage,
    ) -> None:
        snapshot = make_subscription_snapshot(benefit_id=package.id)
        grant = await _apply(snapshot, make_grant_command())
        first_revoked_at = datetime.datetime.now(tz=datetime.UTC)
        first_revocation = await _apply(
            snapshot,
            make_revoke_command(
                subscription_target=InternalSubscriptionTarget(subscription_id=grant.subscription_id),
                revokes_transaction_id=grant.transaction_id,
                effective_at=first_revoked_at,
            ),
        )
        later_revoked_at = first_revoked_at + datetime.timedelta(seconds=1)

        with capture_logs() as logs:
            second_revocation = await _apply(
                snapshot,
                make_revoke_command(
                    subscription_target=InternalSubscriptionTarget(subscription_id=grant.subscription_id),
                    revokes_transaction_id=grant.transaction_id,
                    effective_at=later_revoked_at,
                ),
            )

        source = await entitlement_operations.load_source_entitlement(
            execute,
            snapshot.user_id,
            EntitlementKindId.day_tokens,
            domain.BENEFITS_ENTITLEMENT_SOURCE_ID,
            grant.transaction_id,
        )
        assert source is not None
        assert source.revoked_at == first_revoked_at
        assert source.revoked_by_transaction_id == first_revocation.transaction_id
        assert second_revocation.transaction_created
        assert_logs_has_no_business_event(logs, "subscription_changed")
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_revocation_entitlement_failure_rolls_back_transaction_and_subscription(
        self,
        package: BenefitPackage,
        mocker: MockerFixture,
    ) -> None:
        snapshot = make_subscription_snapshot(benefit_id=package.id)
        grant = await _apply(snapshot, make_grant_command())
        updated_snapshot = snapshot.replace(
            status=SubscriptionStatusId.ended,
            provider_status="canceled",
            provider_updated_at=snapshot.provider_updated_at + datetime.timedelta(seconds=1),
        )
        command = make_revoke_command(
            subscription_target=InternalSubscriptionTarget(subscription_id=grant.subscription_id),
            revokes_transaction_id=grant.transaction_id,
        )
        mocker.patch.object(
            entitlement_domain,
            "revoke_source_entitlements",
            side_effect=RuntimeError("missing source entitlement"),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("b_transactions"),
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(RuntimeError, match="missing source entitlement"):
                    await _apply(updated_snapshot, command)

        assert (
            await operations.load_benefit_transaction_by_source(
                execute,
                source_id=command.source_id,
                source_transaction_id=command.source_transaction_id,
            )
            is None
        )
        assert await subscription_domain.get_subscription(grant.subscription_id) == snapshot.with_identity(
            subscription_id=grant.subscription_id,
            state_transaction_id=grant.transaction_id,
        )
        source = await entitlement_operations.load_source_entitlement(
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
