import asyncio
import datetime
import uuid
from collections.abc import Callable
from typing import cast

import pytest
from pytest_mock import MockerFixture

from ffun.audit import domain as audit_domain
from ffun.audit.entities import AuditEntityKind
from ffun.core.postgresql import ExecuteType, execute, transaction
from ffun.core.tests.helpers import (
    TableSizeDelta,
    TableSizeNotChanged,
    assert_logs_has_business_event,
    assert_logs_has_no_business_event,
    capture_logs,
)
from ffun.domain.domain import new_user_id
from ffun.domain.entities import (
    BenefitId,
    BenefitTransactionId,
    ProviderStatus,
    PurchasedStateSaveOutcome,
    SerializedId,
    SubscriptionId,
)
from ffun.locks.entities import LockKind
from ffun.subscriptions import domain, errors, operations
from ffun.subscriptions.entities import (
    Subscription,
    SubscriptionSaveResult,
    SubscriptionStatusId,
)
from ffun.subscriptions.tests.make import make_subscription

_ACTOR_KIND = AuditEntityKind.psp
_ACTOR_ID = SerializedId("provider-hook")


async def _current_transaction_id(transaction_execute: ExecuteType) -> int:
    rows = await transaction_execute("SELECT txid_current() AS transaction_id")
    return int(rows[0]["transaction_id"])


async def _save_subscription(
    subscription: Subscription,
    *,
    emit_event: bool = True,
) -> tuple[SubscriptionSaveResult, Callable[[], None]]:
    async with transaction() as transaction_execute:
        result, callback = await domain.save_subscription(
            transaction_execute,
            subscription.id,
            subscription.state_transaction_id,
            subscription,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

    if emit_event:
        callback()

    return result, callback


class TestDecideSubscriptionSave:
    def test_missing_subscription_is_created(self) -> None:
        incoming = make_subscription()

        assert domain._decide_subscription_save(None, incoming) == (
            domain._SaveSubscriptionCommand.upsert,
            PurchasedStateSaveOutcome.created,
        )

    def test_stale_snapshot_is_ignored(self) -> None:
        stored = make_subscription()
        incoming = stored.replace(
            status=SubscriptionStatusId.ended,
            provider_updated_at=stored.provider_updated_at - datetime.timedelta(seconds=1),
        )

        assert domain._decide_subscription_save(stored, incoming) == (
            domain._SaveSubscriptionCommand.ignore,
            PurchasedStateSaveOutcome.stale,
        )

    def test_identical_snapshot_is_ignored(self) -> None:
        subscription = make_subscription()

        assert domain._decide_subscription_save(subscription, subscription) == (
            domain._SaveSubscriptionCommand.ignore,
            PurchasedStateSaveOutcome.same,
        )

    def test_freshness_only_snapshot_is_upserted_and_refreshed(self) -> None:
        stored = make_subscription()
        incoming = stored.replace(provider_updated_at=stored.provider_updated_at + datetime.timedelta(seconds=1))

        assert domain._decide_subscription_save(stored, incoming) == (
            domain._SaveSubscriptionCommand.upsert,
            PurchasedStateSaveOutcome.refreshed,
        )

    def test_newer_business_state_is_updated(self) -> None:
        stored = make_subscription()
        incoming = stored.replace(
            benefit_id=BenefitId("replacement-benefit"),
            provider_updated_at=stored.provider_updated_at + datetime.timedelta(seconds=1),
        )

        assert domain._decide_subscription_save(stored, incoming) == (
            domain._SaveSubscriptionCommand.upsert,
            PurchasedStateSaveOutcome.updated,
        )

    def test_same_time_different_business_state_is_conflict(self) -> None:
        stored = make_subscription()

        with pytest.raises(errors.SubscriptionConflict):
            domain._decide_subscription_save(stored, stored.replace(status=SubscriptionStatusId.ended))

    def test_different_user_is_conflict(self) -> None:
        stored = make_subscription()

        with pytest.raises(errors.SubscriptionConflict):
            domain._decide_subscription_save(stored, stored.replace(user_id=new_user_id()))


class TestEmptyBusinessEventCallback:
    def test_emits_no_business_event(self) -> None:
        with capture_logs() as logs:
            domain._empty_business_event_callback()

        assert_logs_has_no_business_event(logs, "subscription_changed")


class TestEmitSubscriptionChangeEvent:
    def test_created_subscription_has_no_previous_status(self) -> None:
        subscription = make_subscription()
        result = SubscriptionSaveResult(
            outcome=PurchasedStateSaveOutcome.created,
            current=subscription,
        )

        with capture_logs() as logs:
            domain._emit_subscription_change_event(result)

        assert_logs_has_business_event(
            logs,
            "subscription_changed",
            user_id=subscription.user_id,
            subscription_id=str(subscription.id),
            state_transaction_id=str(subscription.state_transaction_id),
            previous_status=None,
            status=subscription.status.value,
        )
        assert sum(record.get("event") == "subscription_changed" for record in logs) == 1

    def test_updated_subscription_has_previous_status(self) -> None:
        previous = make_subscription(status=SubscriptionStatusId.active)
        current = previous.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=SubscriptionStatusId.ended,
            provider_status=ProviderStatus("canceled"),
            provider_updated_at=previous.provider_updated_at + datetime.timedelta(seconds=1),
        )
        result = SubscriptionSaveResult(
            outcome=PurchasedStateSaveOutcome.updated,
            current=current,
            previous=previous,
        )

        with capture_logs() as logs:
            domain._emit_subscription_change_event(result)

        assert_logs_has_business_event(
            logs,
            "subscription_changed",
            user_id=current.user_id,
            subscription_id=str(current.id),
            state_transaction_id=str(current.state_transaction_id),
            previous_status=previous.status.value,
            status=current.status.value,
        )
        assert sum(record.get("event") == "subscription_changed" for record in logs) == 1


class TestLockSubscription:
    @pytest.mark.asyncio
    async def test_locks_subscription_identity(self, mocker: MockerFixture) -> None:
        subscription_id = make_subscription().id
        transaction_execute = cast(ExecuteType, mocker.Mock())
        lock_factory = mocker.patch.object(domain, "Lock")

        async with domain.lock_subscription(transaction_execute, subscription_id):
            pass

        lock_factory.assert_called_once_with(
            transaction_execute,
            LockKind("subscription_state"),
            subscription_id,
        )


class TestSaveSubscription:
    @pytest.mark.asyncio
    async def test_uses_subscription_lock(self, mocker: MockerFixture) -> None:
        subscription = make_subscription()
        lock_subscription = mocker.spy(domain, "lock_subscription")

        await _save_subscription(subscription, emit_event=False)

        lock_subscription.assert_called_once_with(
            cast(object, mocker.ANY),
            subscription.id,
        )

    @pytest.mark.asyncio
    async def test_same_identity_cannot_load_while_first_save_holds_lock(self, mocker: MockerFixture) -> None:
        subscription = make_subscription()
        first_load_entered = asyncio.Event()
        release_first_load = asyncio.Event()
        second_save_attempting = asyncio.Event()
        second_load_entered = asyncio.Event()
        load_call_count = 0
        original_load_subscription = operations.load_subscription

        async def tracked_load_subscription(
            transaction_execute: ExecuteType,
            subscription_id: SubscriptionId,
        ) -> Subscription | None:
            nonlocal load_call_count
            load_call_count += 1

            if load_call_count == 1:
                first_load_entered.set()
                await release_first_load.wait()
            else:
                second_load_entered.set()

            return await original_load_subscription(transaction_execute, subscription_id)

        async def save_once(*, announce: bool = False) -> SubscriptionSaveResult:
            if announce:
                second_save_attempting.set()

            result, _ = await _save_subscription(subscription, emit_event=False)
            return result

        mocker.patch.object(operations, "load_subscription", side_effect=tracked_load_subscription)

        first_save = asyncio.create_task(save_once())
        await first_load_entered.wait()
        second_save = asyncio.create_task(save_once(announce=True))
        await second_save_attempting.wait()

        try:
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(0.05):
                    await second_load_entered.wait()
        finally:
            release_first_load.set()
            first_result, second_result = await asyncio.gather(first_save, second_save)

        assert second_load_entered.is_set()
        assert first_result.outcome == PurchasedStateSaveOutcome.created
        assert second_result.outcome == PurchasedStateSaveOutcome.same

    @pytest.mark.asyncio
    async def test_different_identities_do_not_share_lock(self, mocker: MockerFixture) -> None:
        first_subscription = make_subscription()
        second_subscription = make_subscription()
        first_load_entered = asyncio.Event()
        release_first_load = asyncio.Event()
        second_load_entered = asyncio.Event()
        original_load_subscription = operations.load_subscription

        async def tracked_load_subscription(
            transaction_execute: ExecuteType,
            subscription_id: SubscriptionId,
        ) -> Subscription | None:
            if subscription_id == first_subscription.id:
                first_load_entered.set()
                await release_first_load.wait()
            elif subscription_id == second_subscription.id:
                second_load_entered.set()

            return await original_load_subscription(transaction_execute, subscription_id)

        mocker.patch.object(operations, "load_subscription", side_effect=tracked_load_subscription)

        first_save = asyncio.create_task(_save_subscription(first_subscription, emit_event=False))
        await first_load_entered.wait()
        second_save = asyncio.create_task(_save_subscription(second_subscription, emit_event=False))

        try:
            async with asyncio.timeout(0.5):
                await second_load_entered.wait()
        finally:
            release_first_load.set()
            (first_result, _), (second_result, _) = await asyncio.gather(first_save, second_save)

        assert first_result.outcome == PurchasedStateSaveOutcome.created
        assert second_result.outcome == PurchasedStateSaveOutcome.created

    @pytest.mark.asyncio
    async def test_creation_persists_audit_and_returns_post_commit_business_event(self) -> None:
        subscription = make_subscription()

        with capture_logs() as logs:
            async with (
                TableSizeDelta("sb_subscriptions", delta=1),
                TableSizeDelta("a_records", delta=1),
            ):
                result, callback = await _save_subscription(subscription, emit_event=False)

            assert_logs_has_no_business_event(logs, "subscription_changed")
            callback()

        assert result == SubscriptionSaveResult(
            outcome=PurchasedStateSaveOutcome.created,
            current=subscription,
        )
        records = await audit_domain.load_records_for_subject(
            execute,
            subject_kind=AuditEntityKind.user,
            subject_id=SerializedId(str(subscription.user_id)),
        )
        record = records[-1]
        assert record.event == "subscription_changed"
        assert record.actor_kind == _ACTOR_KIND
        assert record.actor_id == _ACTOR_ID
        assert record.attributes == {
            "subscription_id": str(subscription.id),
            "state_transaction_id": str(subscription.state_transaction_id),
            "previous_state": None,
            "new_state": subscription.audit_state(),
        }
        assert_logs_has_business_event(
            logs,
            "subscription_changed",
            user_id=subscription.user_id,
            subscription_id=str(subscription.id),
            state_transaction_id=str(subscription.state_transaction_id),
            previous_status=None,
            status=subscription.status.value,
        )
        assert sum(record.get("event") == "subscription_changed" for record in logs) == 1

    @pytest.mark.asyncio
    async def test_stale_snapshot_is_no_op_and_preserves_state_transaction(self) -> None:
        stored = make_subscription()
        await _save_subscription(stored)
        stale = stored.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=SubscriptionStatusId.ended,
            provider_updated_at=stored.provider_updated_at - datetime.timedelta(seconds=1),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("a_records"),
            ):
                result, callback = await _save_subscription(stale, emit_event=False)
            callback()

        assert result == SubscriptionSaveResult(
            outcome=PurchasedStateSaveOutcome.stale,
            current=stored,
        )
        assert await domain.get_subscription(stored.id) == stored
        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    async def test_same_snapshot_is_idempotent_no_op_and_preserves_state_transaction(self) -> None:
        stored = make_subscription()
        await _save_subscription(stored)
        retry = stored.replace(state_transaction_id=BenefitTransactionId(uuid.uuid4()))

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("a_records"),
            ):
                result, callback = await _save_subscription(retry, emit_event=False)
            callback()

        assert result == SubscriptionSaveResult(
            outcome=PurchasedStateSaveOutcome.same,
            current=stored,
        )
        assert await domain.get_subscription(stored.id) == stored
        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    async def test_same_provider_time_with_different_state_is_conflict(self) -> None:
        subscription = make_subscription()
        await _save_subscription(subscription)
        conflicting = subscription.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=SubscriptionStatusId.ended,
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(errors.SubscriptionConflict):
                    await _save_subscription(conflicting)

        assert await domain.get_subscription(subscription.id) == subscription
        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    async def test_newer_business_state_replaces_snapshot_and_records_change(self) -> None:
        subscription = make_subscription()
        await _save_subscription(subscription)
        replacement = subscription.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            benefit_id=BenefitId("replacement-benefit"),
            status=SubscriptionStatusId.ended,
            provider_status=ProviderStatus("canceled"),
            ends_at=subscription.provider_updated_at,
            provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=1),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeDelta("a_records", delta=1),
            ):
                result, callback = await _save_subscription(replacement, emit_event=False)

            assert_logs_has_no_business_event(logs, "subscription_changed")
            callback()

        assert result == SubscriptionSaveResult(
            outcome=PurchasedStateSaveOutcome.updated,
            current=replacement,
            previous=subscription,
        )
        assert await operations.load_subscription(execute, subscription.id) == replacement
        records = await audit_domain.load_records_for_subject(
            execute,
            subject_kind=AuditEntityKind.user,
            subject_id=SerializedId(str(subscription.user_id)),
        )
        assert records[-1].attributes == {
            "subscription_id": str(subscription.id),
            "state_transaction_id": str(replacement.state_transaction_id),
            "previous_state": subscription.audit_state(),
            "new_state": replacement.audit_state(),
        }
        assert_logs_has_business_event(
            logs,
            "subscription_changed",
            user_id=subscription.user_id,
            subscription_id=str(subscription.id),
            state_transaction_id=str(replacement.state_transaction_id),
            previous_status=subscription.status.value,
            status=replacement.status.value,
        )
        assert sum(record.get("event") == "subscription_changed" for record in logs) == 1

    @pytest.mark.asyncio
    async def test_newer_identical_business_state_advances_causality_without_change_event(self) -> None:
        subscription = make_subscription()
        await _save_subscription(subscription)
        advanced = subscription.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=1),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("a_records"),
            ):
                result, callback = await _save_subscription(advanced, emit_event=False)
            callback()

        assert result == SubscriptionSaveResult(
            outcome=PurchasedStateSaveOutcome.refreshed,
            current=advanced,
        )
        assert await operations.load_subscription(execute, subscription.id) == advanced
        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    async def test_reusing_identity_with_different_user_is_conflict(self) -> None:
        subscription = make_subscription()
        await _save_subscription(subscription)
        conflicting = subscription.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            user_id=new_user_id(),
            provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=1),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(errors.SubscriptionConflict):
                    await _save_subscription(conflicting)

        assert await domain.get_subscription(subscription.id) == subscription
        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    async def test_audit_failure_rolls_back_replacement_and_event(self, mocker: MockerFixture) -> None:
        subscription = make_subscription()
        await _save_subscription(subscription)
        replacement = subscription.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=SubscriptionStatusId.ended,
            provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=1),
        )
        mocker.patch.object(audit_domain, "record", side_effect=RuntimeError("audit failed"))

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(RuntimeError, match="audit failed"):
                    await _save_subscription(replacement)

        assert await operations.load_subscription(execute, subscription.id) == subscription
        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    async def test_concurrent_replacements_cannot_leave_older_state(self) -> None:
        subscription = make_subscription()
        await _save_subscription(subscription)
        older = subscription.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=SubscriptionStatusId.paused,
            provider_status=ProviderStatus("paused"),
            provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=1),
        )
        newer = subscription.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=SubscriptionStatusId.ended,
            provider_status=ProviderStatus("canceled"),
            ends_at=subscription.provider_updated_at + datetime.timedelta(seconds=2),
            provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=2),
        )

        await asyncio.gather(
            _save_subscription(older),
            _save_subscription(newer),
        )

        assert await operations.load_subscription(execute, subscription.id) == newer


class TestNewSubscriptionId:
    def test_reexports_operation(self) -> None:
        assert domain.new_subscription_id is operations.new_subscription_id


class TestLoadSubscription:
    def test_reexports_operation(self) -> None:
        assert domain.load_subscription is operations.load_subscription


class TestLoadSubscriptionIdsByBenefit:
    def test_reexports_operation(self) -> None:
        assert domain.load_subscription_ids_by_benefit is operations.load_subscription_ids_by_benefit


class TestLoadProviderSubscriptionReference:
    def test_reexports_operation(self) -> None:
        assert domain.load_provider_subscription_reference is operations.load_provider_subscription_reference


class TestResolveProviderSubscriptionReference:
    def test_reexports_operation(self) -> None:
        assert domain.resolve_provider_subscription_reference is operations.resolve_provider_subscription_reference


class TestGetSubscription:
    @pytest.mark.asyncio
    async def test_returns_exact_snapshot_or_none(self) -> None:
        subscription = make_subscription()
        await _save_subscription(subscription)

        assert await domain.get_subscription(subscription.id) == subscription
        assert await domain.get_subscription(domain.new_subscription_id()) is None


class TestGetSubscriptionsForUser:
    @pytest.mark.asyncio
    async def test_empty_statuses_returns_empty_list(self) -> None:
        user_id = new_user_id()

        assert await domain.get_subscriptions_for_user(user_id, statuses=[]) == []

    @pytest.mark.asyncio
    async def test_filters_by_statuses(self) -> None:
        user_id = new_user_id()
        active = make_subscription(user_id=user_id)
        ended = make_subscription(
            user_id=user_id,
            status=SubscriptionStatusId.ended,
        )
        await _save_subscription(active)
        await _save_subscription(ended)

        assert await domain.get_subscriptions_for_user(
            user_id,
            statuses=[SubscriptionStatusId.ended],
        ) == [ended]

    @pytest.mark.asyncio
    async def test_returns_all_statuses_in_order_without_side_effects(self) -> None:
        selected_user_id = new_user_id()
        other_user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        ended = make_subscription(
            user_id=selected_user_id,
            status=SubscriptionStatusId.ended,
            provider_status=ProviderStatus("canceled"),
            started_at=now - datetime.timedelta(days=1),
            ends_at=now,
        )
        active = make_subscription(
            user_id=selected_user_id,
            started_at=now,
        )
        other = make_subscription(user_id=other_user_id)
        await _save_subscription(ended)
        await _save_subscription(active)
        await _save_subscription(other)

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sb_subscriptions"),
                TableSizeNotChanged("a_records"),
            ):
                subscriptions = await domain.get_subscriptions_for_user(selected_user_id)

        assert subscriptions == [active, ended]
        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    async def test_operation_database_requests_share_domain_transaction(self, mocker: MockerFixture) -> None:
        subscription = make_subscription()
        transaction_ids: list[int] = []

        async def load_subscriptions(transaction_execute: ExecuteType, *_: object, **__: object) -> list[Subscription]:
            transaction_ids.append(await _current_transaction_id(transaction_execute))
            transaction_ids.append(await _current_transaction_id(transaction_execute))
            return [subscription]

        mocker.patch.object(operations, "load_subscriptions", side_effect=load_subscriptions)

        result = await domain.get_subscriptions_for_user(subscription.user_id)

        assert result == [subscription]
        assert len(set(transaction_ids)) == 1


class TestGetAliveSubscriptionsForUser:
    def test_alive_statuses(self) -> None:
        assert domain.ALIVE_SUBSCRIPTION_STATUSES == [
            SubscriptionStatusId.pending,
            SubscriptionStatusId.trialing,
            SubscriptionStatusId.active,
            SubscriptionStatusId.past_due,
            SubscriptionStatusId.paused,
        ]

    @pytest.mark.asyncio
    async def test_no_subscriptions_returns_empty_list(self) -> None:
        assert await domain.get_alive_subscriptions_for_user(new_user_id()) == []

    @pytest.mark.asyncio
    async def test_returns_only_alive_subscriptions(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        alive_without_end = make_subscription(
            user_id=user_id,
            started_at=now,
        )
        alive_until_future = make_subscription(
            user_id=user_id,
            started_at=now - datetime.timedelta(seconds=1),
            ends_at=now + datetime.timedelta(days=1),
        )
        expired = make_subscription(
            user_id=user_id,
            started_at=now - datetime.timedelta(seconds=2),
            ends_at=now - datetime.timedelta(seconds=1),
        )
        ending_at_evaluation = make_subscription(
            user_id=user_id,
            started_at=now - datetime.timedelta(seconds=3),
            ends_at=now,
        )
        ended = make_subscription(
            user_id=user_id,
            status=SubscriptionStatusId.ended,
            started_at=now - datetime.timedelta(seconds=4),
            ends_at=now + datetime.timedelta(days=1),
        )
        for subscription in (alive_without_end, alive_until_future, expired, ending_at_evaluation, ended):
            await _save_subscription(subscription)

        assert await domain.get_alive_subscriptions_for_user(user_id) == [alive_without_end, alive_until_future]
