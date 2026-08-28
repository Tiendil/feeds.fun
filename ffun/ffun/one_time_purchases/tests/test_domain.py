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
    OneTimePurchaseId,
    ProviderStatus,
    PurchasedStateSaveOutcome,
    SerializedId,
)
from ffun.locks.entities import LockKind
from ffun.one_time_purchases import domain, errors, operations
from ffun.one_time_purchases.entities import (
    Purchase,
    PurchaseSaveResult,
    PurchaseStatus,
)
from ffun.one_time_purchases.tests.make import make_purchase

_ACTOR_KIND = AuditEntityKind.psp
_ACTOR_ID = SerializedId("provider-hook")


async def _current_transaction_id(transaction_execute: ExecuteType) -> int:
    rows = await transaction_execute("SELECT txid_current() AS transaction_id")
    return int(rows[0]["transaction_id"])


async def _save_purchase(
    purchase: Purchase,
    *,
    emit_event: bool = True,
) -> tuple[PurchaseSaveResult, Callable[[], None]]:
    async with transaction() as transaction_execute:
        result, callback = await domain.save_purchase(
            transaction_execute,
            purchase.id,
            purchase.state_transaction_id,
            purchase,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

    if emit_event:
        callback()

    return result, callback


class TestDecidePurchaseSave:
    def test_missing_purchase_is_created(self) -> None:
        incoming = make_purchase()

        assert domain._decide_purchase_save(None, incoming) == PurchasedStateSaveOutcome.created

    def test_stale_snapshot_is_ignored(self) -> None:
        stored = make_purchase()
        incoming = stored.replace(
            status=PurchaseStatus.refunded,
            provider_updated_at=stored.provider_updated_at - datetime.timedelta(seconds=1),
        )

        assert domain._decide_purchase_save(stored, incoming) == PurchasedStateSaveOutcome.stale

    def test_identical_snapshot_is_ignored(self) -> None:
        purchase = make_purchase()

        assert domain._decide_purchase_save(purchase, purchase) == PurchasedStateSaveOutcome.same

    def test_freshness_only_snapshot_is_upserted_and_refreshed(self) -> None:
        stored = make_purchase()
        incoming = stored.replace(provider_updated_at=stored.provider_updated_at + datetime.timedelta(seconds=1))

        assert domain._decide_purchase_save(stored, incoming) == PurchasedStateSaveOutcome.refreshed

    def test_newer_business_state_is_updated(self) -> None:
        stored = make_purchase()
        incoming = stored.replace(
            status=PurchaseStatus.refunded,
            provider_updated_at=stored.provider_updated_at + datetime.timedelta(seconds=1),
        )

        assert domain._decide_purchase_save(stored, incoming) == PurchasedStateSaveOutcome.updated

    def test_same_time_different_business_state_is_conflict(self) -> None:
        stored = make_purchase()

        with pytest.raises(errors.PurchaseConflict):
            domain._decide_purchase_save(stored, stored.replace(status=PurchaseStatus.refunded))

    def test_different_user_is_conflict(self) -> None:
        stored = make_purchase()

        with pytest.raises(errors.PurchaseConflict):
            domain._decide_purchase_save(stored, stored.replace(user_id=new_user_id()))

    def test_different_benefit_is_conflict(self) -> None:
        stored = make_purchase()

        with pytest.raises(errors.PurchaseConflict):
            domain._decide_purchase_save(stored, stored.replace(benefit_id=BenefitId("other-benefit")))


class TestEmptyBusinessEventCallback:
    def test_emits_no_business_event(self) -> None:
        with capture_logs() as logs:
            domain._empty_business_event_callback()

        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")


class TestEmitPurchaseChangeEvent:
    def test_created_purchase_has_no_previous_status(self) -> None:
        purchase = make_purchase()
        result = PurchaseSaveResult(
            outcome=PurchasedStateSaveOutcome.created,
            current=purchase,
        )

        with capture_logs() as logs:
            domain._emit_purchase_change_event(result)

        assert_logs_has_business_event(
            logs,
            "one_time_purchase_changed",
            user_id=purchase.user_id,
            one_time_purchase_id=str(purchase.id),
            state_transaction_id=str(purchase.state_transaction_id),
            previous_status=None,
            status=purchase.status.value,
        )
        assert sum(record.get("event") == "one_time_purchase_changed" for record in logs) == 1

    def test_updated_purchase_has_previous_status(self) -> None:
        previous = make_purchase(status=PurchaseStatus.completed)
        current = previous.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=PurchaseStatus.refunded,
            provider_status=ProviderStatus("refunded"),
            provider_updated_at=previous.provider_updated_at + datetime.timedelta(seconds=1),
        )
        result = PurchaseSaveResult(
            outcome=PurchasedStateSaveOutcome.updated,
            current=current,
            previous=previous,
        )

        with capture_logs() as logs:
            domain._emit_purchase_change_event(result)

        assert_logs_has_business_event(
            logs,
            "one_time_purchase_changed",
            user_id=current.user_id,
            one_time_purchase_id=str(current.id),
            state_transaction_id=str(current.state_transaction_id),
            previous_status=previous.status.value,
            status=current.status.value,
        )
        assert sum(record.get("event") == "one_time_purchase_changed" for record in logs) == 1


class TestSavePurchase:
    @pytest.mark.asyncio
    async def test_locks_internal_purchase_identity(self, mocker: MockerFixture) -> None:
        purchase = make_purchase()
        lock_factory = mocker.patch.object(domain, "Lock")

        await _save_purchase(purchase, emit_event=False)

        lock_factory.assert_called_once_with(
            cast(object, mocker.ANY),
            LockKind("one_time_purchase_state"),
            purchase.id,
        )

    @pytest.mark.asyncio
    async def test_same_identity_cannot_load_while_first_save_holds_lock(self, mocker: MockerFixture) -> None:
        purchase = make_purchase()
        first_load_entered = asyncio.Event()
        release_first_load = asyncio.Event()
        second_save_attempting = asyncio.Event()
        second_load_entered = asyncio.Event()
        load_call_count = 0
        original_load_purchase = operations.load_purchase

        async def tracked_load_purchase(
            transaction_execute: ExecuteType,
            one_time_purchase_id: OneTimePurchaseId,
        ) -> Purchase | None:
            nonlocal load_call_count
            load_call_count += 1

            if load_call_count == 1:
                first_load_entered.set()
                await release_first_load.wait()
            else:
                second_load_entered.set()

            return await original_load_purchase(transaction_execute, one_time_purchase_id)

        async def save_once(*, announce: bool = False) -> PurchaseSaveResult:
            if announce:
                second_save_attempting.set()

            result, _ = await _save_purchase(purchase, emit_event=False)
            return result

        mocker.patch.object(operations, "load_purchase", side_effect=tracked_load_purchase)

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
        first_purchase = make_purchase()
        second_purchase = make_purchase()
        first_load_entered = asyncio.Event()
        release_first_load = asyncio.Event()
        second_load_entered = asyncio.Event()
        original_load_purchase = operations.load_purchase

        async def tracked_load_purchase(
            transaction_execute: ExecuteType,
            one_time_purchase_id: OneTimePurchaseId,
        ) -> Purchase | None:
            if one_time_purchase_id == first_purchase.id:
                first_load_entered.set()
                await release_first_load.wait()
            elif one_time_purchase_id == second_purchase.id:
                second_load_entered.set()

            return await original_load_purchase(transaction_execute, one_time_purchase_id)

        mocker.patch.object(operations, "load_purchase", side_effect=tracked_load_purchase)

        first_save = asyncio.create_task(_save_purchase(first_purchase, emit_event=False))
        await first_load_entered.wait()
        second_save = asyncio.create_task(_save_purchase(second_purchase, emit_event=False))

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
        purchase = make_purchase()

        with capture_logs() as logs:
            async with (
                TableSizeDelta("otp_purchases", delta=1),
                TableSizeDelta("a_records", delta=1),
            ):
                result, callback = await _save_purchase(purchase, emit_event=False)

            assert_logs_has_no_business_event(logs, "one_time_purchase_changed")
            callback()

        assert result == PurchaseSaveResult(
            outcome=PurchasedStateSaveOutcome.created,
            current=purchase,
        )
        records = await audit_domain.load_records_for_subject(
            execute,
            subject_kind=AuditEntityKind.user,
            subject_id=SerializedId(str(purchase.user_id)),
        )
        record = records[-1]
        assert record.event == "one_time_purchase_changed"
        assert record.actor_kind == _ACTOR_KIND
        assert record.actor_id == _ACTOR_ID
        assert record.attributes == {
            "one_time_purchase_id": str(purchase.id),
            "state_transaction_id": str(purchase.state_transaction_id),
            "previous_state": None,
            "new_state": purchase.audit_state(),
        }
        assert_logs_has_business_event(
            logs,
            "one_time_purchase_changed",
            user_id=purchase.user_id,
            one_time_purchase_id=str(purchase.id),
            state_transaction_id=str(purchase.state_transaction_id),
            previous_status=None,
            status=purchase.status.value,
        )
        assert sum(record.get("event") == "one_time_purchase_changed" for record in logs) == 1

    @pytest.mark.asyncio
    async def test_stale_snapshot_is_no_op_and_preserves_state_transaction(self) -> None:
        stored = make_purchase()
        await _save_purchase(stored)
        stale = stored.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=PurchaseStatus.refunded,
            provider_updated_at=stored.provider_updated_at - datetime.timedelta(seconds=1),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("otp_purchases"),
                TableSizeNotChanged("a_records"),
            ):
                result, callback = await _save_purchase(stale, emit_event=False)
            callback()

        assert result == PurchaseSaveResult(
            outcome=PurchasedStateSaveOutcome.stale,
            current=stored,
        )
        assert await domain.get_purchase(stored.id) == stored
        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")

    @pytest.mark.asyncio
    async def test_same_snapshot_is_idempotent_no_op_and_preserves_state_transaction(self) -> None:
        stored = make_purchase()
        await _save_purchase(stored)
        retry = stored.replace(state_transaction_id=BenefitTransactionId(uuid.uuid4()))

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("otp_purchases"),
                TableSizeNotChanged("a_records"),
            ):
                result, callback = await _save_purchase(retry, emit_event=False)
            callback()

        assert result == PurchaseSaveResult(
            outcome=PurchasedStateSaveOutcome.same,
            current=stored,
        )
        assert await domain.get_purchase(stored.id) == stored
        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")

    @pytest.mark.asyncio
    async def test_same_provider_time_with_different_state_is_conflict(self) -> None:
        purchase = make_purchase()
        await _save_purchase(purchase)
        conflicting = purchase.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=PurchaseStatus.refunded,
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("otp_purchases"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(errors.PurchaseConflict):
                    await _save_purchase(conflicting)

        assert await domain.get_purchase(purchase.id) == purchase
        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")

    @pytest.mark.asyncio
    async def test_newer_business_state_replaces_snapshot_and_records_change(self) -> None:
        purchase = make_purchase()
        await _save_purchase(purchase)
        replacement = purchase.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=PurchaseStatus.refunded,
            provider_status=ProviderStatus("refunded"),
            provider_updated_at=purchase.provider_updated_at + datetime.timedelta(seconds=1),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("otp_purchases"),
                TableSizeDelta("a_records", delta=1),
            ):
                result, callback = await _save_purchase(replacement, emit_event=False)

            assert_logs_has_no_business_event(logs, "one_time_purchase_changed")
            callback()

        assert result == PurchaseSaveResult(
            outcome=PurchasedStateSaveOutcome.updated,
            current=replacement,
            previous=purchase,
        )
        assert await operations.load_purchase(execute, purchase.id) == replacement
        records = await audit_domain.load_records_for_subject(
            execute,
            subject_kind=AuditEntityKind.user,
            subject_id=SerializedId(str(purchase.user_id)),
        )
        assert records[-1].attributes == {
            "one_time_purchase_id": str(purchase.id),
            "state_transaction_id": str(replacement.state_transaction_id),
            "previous_state": purchase.audit_state(),
            "new_state": replacement.audit_state(),
        }
        assert_logs_has_business_event(
            logs,
            "one_time_purchase_changed",
            user_id=purchase.user_id,
            one_time_purchase_id=str(purchase.id),
            state_transaction_id=str(replacement.state_transaction_id),
            previous_status=purchase.status.value,
            status=replacement.status.value,
        )
        assert sum(record.get("event") == "one_time_purchase_changed" for record in logs) == 1

    @pytest.mark.asyncio
    async def test_newer_identical_business_state_advances_causality_without_change_event(self) -> None:
        purchase = make_purchase()
        await _save_purchase(purchase)
        advanced = purchase.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            provider_updated_at=purchase.provider_updated_at + datetime.timedelta(seconds=1),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("otp_purchases"),
                TableSizeNotChanged("a_records"),
            ):
                result, callback = await _save_purchase(advanced, emit_event=False)
            callback()

        assert result == PurchaseSaveResult(
            outcome=PurchasedStateSaveOutcome.refreshed,
            current=advanced,
        )
        assert await operations.load_purchase(execute, purchase.id) == advanced
        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")

    @pytest.mark.asyncio
    async def test_reusing_identity_with_different_user_is_conflict(self) -> None:
        purchase = make_purchase()
        await _save_purchase(purchase)
        conflicting = purchase.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            user_id=new_user_id(),
            provider_updated_at=purchase.provider_updated_at + datetime.timedelta(seconds=1),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("otp_purchases"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(errors.PurchaseConflict):
                    await _save_purchase(conflicting)

        assert await domain.get_purchase(purchase.id) == purchase
        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")

    @pytest.mark.asyncio
    async def test_reusing_identity_with_different_benefit_is_conflict(self) -> None:
        purchase = make_purchase()
        await _save_purchase(purchase)
        conflicting = purchase.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            benefit_id=BenefitId("other-benefit"),
            provider_updated_at=purchase.provider_updated_at + datetime.timedelta(seconds=1),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("otp_purchases"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(errors.PurchaseConflict):
                    await _save_purchase(conflicting)

        assert await domain.get_purchase(purchase.id) == purchase
        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")

    @pytest.mark.asyncio
    async def test_audit_failure_rolls_back_replacement_and_event(self, mocker: MockerFixture) -> None:
        purchase = make_purchase()
        await _save_purchase(purchase)
        replacement = purchase.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=PurchaseStatus.refunded,
            provider_updated_at=purchase.provider_updated_at + datetime.timedelta(seconds=1),
        )
        mocker.patch.object(audit_domain, "record", side_effect=RuntimeError("audit failed"))

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("otp_purchases"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(RuntimeError, match="audit failed"):
                    await _save_purchase(replacement)

        assert await operations.load_purchase(execute, purchase.id) == purchase
        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")

    @pytest.mark.asyncio
    async def test_concurrent_replacements_cannot_leave_older_state(self) -> None:
        purchase = make_purchase()
        await _save_purchase(purchase)
        older = purchase.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=PurchaseStatus.disputed,
            provider_status=ProviderStatus("disputed"),
            provider_updated_at=purchase.provider_updated_at + datetime.timedelta(seconds=1),
        )
        newer = purchase.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=PurchaseStatus.refunded,
            provider_status=ProviderStatus("refunded"),
            provider_updated_at=purchase.provider_updated_at + datetime.timedelta(seconds=2),
        )

        await asyncio.gather(
            _save_purchase(older),
            _save_purchase(newer),
        )

        assert await operations.load_purchase(execute, purchase.id) == newer


class TestNewPurchaseId:
    def test_reexports_operation(self) -> None:
        assert domain.new_purchase_id is operations.new_purchase_id


class TestLoadProviderPurchaseReference:
    def test_reexports_operation(self) -> None:
        assert domain.load_provider_purchase_reference is operations.load_provider_purchase_reference


class TestResolveProviderPurchaseReference:
    def test_reexports_operation(self) -> None:
        assert domain.resolve_provider_purchase_reference is operations.resolve_provider_purchase_reference


class TestGetPurchase:
    @pytest.mark.asyncio
    async def test_returns_exact_snapshot_or_none(self) -> None:
        purchase = make_purchase()
        await _save_purchase(purchase)

        assert await domain.get_purchase(purchase.id) == purchase
        assert await domain.get_purchase(domain.new_purchase_id()) is None


class TestGetPurchasesForUser:
    @pytest.mark.asyncio
    async def test_empty_statuses_returns_empty_list(self) -> None:
        user_id = new_user_id()

        assert await domain.get_purchases_for_user(user_id, statuses=[]) == []

    @pytest.mark.asyncio
    async def test_filters_by_statuses(self) -> None:
        user_id = new_user_id()
        completed = make_purchase(user_id=user_id)
        refunded = make_purchase(user_id=user_id, status=PurchaseStatus.refunded)
        await _save_purchase(completed)
        await _save_purchase(refunded)

        assert await domain.get_purchases_for_user(
            user_id,
            statuses=[PurchaseStatus.refunded],
        ) == [refunded]

    @pytest.mark.asyncio
    async def test_returns_all_statuses_in_order_without_side_effects(self) -> None:
        selected_user_id = new_user_id()
        other_user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        refunded = make_purchase(
            user_id=selected_user_id,
            status=PurchaseStatus.refunded,
            provider_status=ProviderStatus("refunded"),
            purchased_at=now - datetime.timedelta(days=1),
        )
        completed = make_purchase(
            user_id=selected_user_id,
            purchased_at=now,
        )
        other = make_purchase(user_id=other_user_id)
        await _save_purchase(refunded)
        await _save_purchase(completed)
        await _save_purchase(other)

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("otp_purchases"),
                TableSizeNotChanged("a_records"),
            ):
                purchases = await domain.get_purchases_for_user(selected_user_id)

        assert purchases == [completed, refunded]
        assert_logs_has_no_business_event(logs, "one_time_purchase_changed")

    @pytest.mark.asyncio
    async def test_operation_database_requests_share_domain_transaction(self, mocker: MockerFixture) -> None:
        purchase = make_purchase()
        transaction_ids: list[int] = []

        async def load_purchases(transaction_execute: ExecuteType, *_: object, **__: object) -> list[Purchase]:
            transaction_ids.append(await _current_transaction_id(transaction_execute))
            transaction_ids.append(await _current_transaction_id(transaction_execute))
            return [purchase]

        mocker.patch.object(operations, "load_purchases", side_effect=load_purchases)

        result = await domain.get_purchases_for_user(purchase.user_id)

        assert result == [purchase]
        assert len(set(transaction_ids)) == 1
