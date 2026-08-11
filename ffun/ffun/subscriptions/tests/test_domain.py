import asyncio
import datetime
from typing import cast

import pytest
from pytest_mock import MockerFixture

from ffun.audit import domain as audit_domain
from ffun.audit.entities import AuditEntityKind
from ffun.core.postgresql import ExecuteType, execute
from ffun.core.tests.helpers import (
    TableSizeDelta,
    TableSizeNotChanged,
    assert_logs_has_business_event,
    assert_logs_has_no_business_event,
    capture_logs,
)
from ffun.domain.domain import new_user_id
from ffun.domain.entities import SerializedId
from ffun.locks.entities import LockKind
from ffun.subscriptions import domain, errors, operations
from ffun.subscriptions.entities import (
    ProviderCustomerId,
    ProviderId,
    ProviderMerchantId,
    ProviderStatus,
    ProviderSubscriptionId,
    SaveSubscriptionOutcome,
    Subscription,
    SubscriptionStatusId,
)
from ffun.subscriptions.tests.make import make_subscription

_ACTOR_KIND = AuditEntityKind.psp
_ACTOR_ID = SerializedId("provider-hook")


async def _current_transaction_id(transaction_execute: ExecuteType) -> int:
    rows = await transaction_execute("SELECT txid_current() AS transaction_id")
    return int(rows[0]["transaction_id"])


class TestDecideSubscriptionSave:
    def test_missing_subscription_is_created(self) -> None:
        incoming = make_subscription()

        assert domain._decide_subscription_save(None, incoming) == (
            domain._SaveSubscriptionCommand.upsert,
            SaveSubscriptionOutcome.created,
        )

    def test_stale_snapshot_is_ignored(self) -> None:
        stored = make_subscription()
        incoming = stored.replace(
            status=SubscriptionStatusId.ended,
            provider_updated_at=stored.provider_updated_at - datetime.timedelta(seconds=1),
        )

        assert domain._decide_subscription_save(stored, incoming) == (
            domain._SaveSubscriptionCommand.ignore,
            SaveSubscriptionOutcome.skipped,
        )

    def test_identical_snapshot_is_ignored(self) -> None:
        subscription = make_subscription()

        assert domain._decide_subscription_save(subscription, subscription) == (
            domain._SaveSubscriptionCommand.ignore,
            SaveSubscriptionOutcome.skipped,
        )

    def test_freshness_only_snapshot_is_upserted_and_skipped(self) -> None:
        stored = make_subscription()
        incoming = stored.replace(provider_updated_at=stored.provider_updated_at + datetime.timedelta(seconds=1))

        assert domain._decide_subscription_save(stored, incoming) == (
            domain._SaveSubscriptionCommand.upsert,
            SaveSubscriptionOutcome.skipped,
        )

    def test_newer_business_state_is_updated(self) -> None:
        stored = make_subscription()
        incoming = stored.replace(
            status=SubscriptionStatusId.ended,
            provider_updated_at=stored.provider_updated_at + datetime.timedelta(seconds=1),
        )

        assert domain._decide_subscription_save(stored, incoming) == (
            domain._SaveSubscriptionCommand.upsert,
            SaveSubscriptionOutcome.updated,
        )

    def test_same_time_different_business_state_is_conflict(self) -> None:
        stored = make_subscription()

        with pytest.raises(errors.SubscriptionConflict):
            domain._decide_subscription_save(stored, stored.replace(status=SubscriptionStatusId.ended))

    def test_different_ownership_is_conflict(self) -> None:
        stored = make_subscription()

        with pytest.raises(errors.SubscriptionConflict):
            domain._decide_subscription_save(stored, stored.replace(user_id=new_user_id()))


class TestSaveSubscription:
    @pytest.mark.asyncio
    async def test_uses_stable_subscription_identity_lock(self, mocker: MockerFixture) -> None:
        subscription = make_subscription()
        locked_transaction_spy = mocker.spy(domain, "locked_transaction")

        await domain.save_subscription(subscription, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)
        await domain.save_subscription(subscription, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)

        assert locked_transaction_spy.call_count == 2
        first_call, second_call = locked_transaction_spy.call_args_list
        first_arguments = cast(tuple[object, ...], first_call.args)
        second_arguments = cast(tuple[object, ...], second_call.args)
        assert first_arguments[0] == LockKind("subscription_identity")
        assert second_arguments[0] == LockKind("subscription_identity")
        assert first_arguments[1] == second_arguments[1]

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("identity_field", "different_value"),
        [
            ("provider_id", ProviderId("different-provider")),
            ("provider_merchant_id", ProviderMerchantId("different-merchant")),
            ("provider_subscription_id", ProviderSubscriptionId("different-subscription")),
        ],
    )
    async def test_lock_argument_uses_complete_subscription_identity(
        self,
        mocker: MockerFixture,
        identity_field: str,
        different_value: object,
    ) -> None:
        subscription = make_subscription()
        different_subscription = subscription.replace(**{identity_field: different_value})
        locked_transaction_spy = mocker.spy(domain, "locked_transaction")

        await domain.save_subscription(subscription, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)
        await domain.save_subscription(different_subscription, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)

        assert locked_transaction_spy.call_count == 2
        first_call, second_call = locked_transaction_spy.call_args_list
        first_arguments = cast(tuple[object, ...], first_call.args)
        second_arguments = cast(tuple[object, ...], second_call.args)
        assert first_arguments[1] != second_arguments[1]

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
            *,
            provider_id: ProviderId,
            provider_merchant_id: ProviderMerchantId,
            provider_subscription_id: ProviderSubscriptionId,
        ) -> Subscription | None:
            nonlocal load_call_count
            load_call_count += 1

            if load_call_count == 1:
                first_load_entered.set()
                await release_first_load.wait()
            else:
                second_load_entered.set()

            return await original_load_subscription(
                transaction_execute,
                provider_id=provider_id,
                provider_merchant_id=provider_merchant_id,
                provider_subscription_id=provider_subscription_id,
            )

        async def save_second_snapshot() -> SaveSubscriptionOutcome:
            second_save_attempting.set()
            return await domain.save_subscription(subscription, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)

        mocker.patch.object(operations, "load_subscription", side_effect=tracked_load_subscription)

        first_save = asyncio.create_task(
            domain.save_subscription(subscription, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)
        )
        await first_load_entered.wait()
        second_save = asyncio.create_task(save_second_snapshot())
        await second_save_attempting.wait()

        try:
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(0.05):
                    await second_load_entered.wait()
        finally:
            release_first_load.set()
            first_outcome, second_outcome = await asyncio.gather(first_save, second_save)

        assert second_load_entered.is_set()
        assert first_outcome == SaveSubscriptionOutcome.created
        assert second_outcome == SaveSubscriptionOutcome.skipped

    @pytest.mark.asyncio
    async def test_creation_persists_audit_and_emits_complete_business_event(self) -> None:
        subscription = make_subscription()

        with capture_logs() as logs:
            async with (
                TableSizeDelta("sub_subscriptions", delta=1),
                TableSizeDelta("a_records", delta=1),
            ):
                outcome = await domain.save_subscription(
                    subscription,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert outcome == SaveSubscriptionOutcome.created
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
            "provider_id": subscription.provider_id,
            "provider_merchant_id": subscription.provider_merchant_id,
            "provider_subscription_id": subscription.provider_subscription_id,
            "provider_customer_id": subscription.provider_customer_id,
            "previous_state": None,
            "new_state": subscription.audit_state(),
        }
        assert_logs_has_business_event(
            logs,
            "subscription_changed",
            user_id=subscription.user_id,
            previous_status=None,
            status=subscription.status.value,
        )
        assert sum(record.get("event") == "subscription_changed" for record in logs) == 1

    @pytest.mark.asyncio
    async def test_stale_snapshot_is_no_op(self) -> None:
        stored = make_subscription()
        await domain.save_subscription(stored, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)
        stale = stored.replace(
            status=SubscriptionStatusId.ended,
            provider_updated_at=stored.provider_updated_at - datetime.timedelta(seconds=1),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sub_subscriptions"),
                TableSizeNotChanged("a_records"),
            ):
                outcome = await domain.save_subscription(
                    stale,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert outcome == SaveSubscriptionOutcome.skipped
        assert (
            await domain.get_subscription(
                provider_id=stored.provider_id,
                provider_merchant_id=stored.provider_merchant_id,
                provider_subscription_id=stored.provider_subscription_id,
            )
            == stored
        )
        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    async def test_same_snapshot_is_idempotent_no_op(self) -> None:
        subscription = make_subscription()
        await domain.save_subscription(subscription, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sub_subscriptions"),
                TableSizeNotChanged("a_records"),
            ):
                outcome = await domain.save_subscription(
                    subscription,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert outcome == SaveSubscriptionOutcome.skipped
        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    async def test_same_provider_time_with_different_state_is_conflict(self) -> None:
        subscription = make_subscription()
        await domain.save_subscription(subscription, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sub_subscriptions"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(errors.SubscriptionConflict):
                    await domain.save_subscription(
                        subscription.replace(status=SubscriptionStatusId.ended),
                        actor_kind=_ACTOR_KIND,
                        actor_id=_ACTOR_ID,
                    )

        assert (
            await domain.get_subscription(
                provider_id=subscription.provider_id,
                provider_merchant_id=subscription.provider_merchant_id,
                provider_subscription_id=subscription.provider_subscription_id,
            )
            == subscription
        )
        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    async def test_newer_business_state_replaces_snapshot_and_records_change(self) -> None:
        subscription = make_subscription()
        await domain.save_subscription(subscription, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)
        replacement = subscription.replace(
            status=SubscriptionStatusId.ended,
            provider_status=ProviderStatus("canceled"),
            ends_at=subscription.provider_updated_at,
            provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=1),
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sub_subscriptions"),
                TableSizeDelta("a_records", delta=1),
            ):
                outcome = await domain.save_subscription(
                    replacement,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert outcome == SaveSubscriptionOutcome.updated
        assert (
            await operations.load_subscription(
                execute,
                provider_id=subscription.provider_id,
                provider_merchant_id=subscription.provider_merchant_id,
                provider_subscription_id=subscription.provider_subscription_id,
            )
            == replacement
        )
        records = await audit_domain.load_records_for_subject(
            execute,
            subject_kind=AuditEntityKind.user,
            subject_id=SerializedId(str(subscription.user_id)),
        )
        assert records[-1].attributes["previous_state"] == subscription.audit_state()
        assert records[-1].attributes["new_state"] == replacement.audit_state()
        assert_logs_has_business_event(
            logs,
            "subscription_changed",
            user_id=subscription.user_id,
            previous_status=subscription.status.value,
            status=replacement.status.value,
        )
        assert sum(record.get("event") == "subscription_changed" for record in logs) == 1

    @pytest.mark.asyncio
    async def test_newer_identical_business_state_advances_freshness_without_change_event(self) -> None:
        subscription = make_subscription()
        await domain.save_subscription(subscription, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)
        advanced = subscription.replace(
            provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=1)
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sub_subscriptions"),
                TableSizeNotChanged("a_records"),
            ):
                outcome = await domain.save_subscription(
                    advanced,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert outcome == SaveSubscriptionOutcome.skipped
        assert (
            await operations.load_subscription(
                execute,
                provider_id=subscription.provider_id,
                provider_merchant_id=subscription.provider_merchant_id,
                provider_subscription_id=subscription.provider_subscription_id,
            )
            == advanced
        )
        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("immutable_field", ["user_id", "provider_customer_id"])
    async def test_reusing_identity_with_different_ownership_is_conflict(self, immutable_field: str) -> None:
        subscription = make_subscription()
        await domain.save_subscription(subscription, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)
        changed_value = new_user_id() if immutable_field == "user_id" else ProviderCustomerId("different-customer")
        conflicting = subscription.replace(
            **{
                immutable_field: changed_value,
                "provider_updated_at": subscription.provider_updated_at + datetime.timedelta(seconds=1),
            }
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sub_subscriptions"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(errors.SubscriptionConflict):
                    await domain.save_subscription(
                        conflicting,
                        actor_kind=_ACTOR_KIND,
                        actor_id=_ACTOR_ID,
                    )

        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    async def test_audit_failure_rolls_back_subscription_and_event(self, mocker: MockerFixture) -> None:
        subscription = make_subscription()
        mocker.patch.object(audit_domain, "record", side_effect=RuntimeError("audit failed"))

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sub_subscriptions"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(RuntimeError, match="audit failed"):
                    await domain.save_subscription(
                        subscription,
                        actor_kind=_ACTOR_KIND,
                        actor_id=_ACTOR_ID,
                    )

        assert (
            await operations.load_subscription(
                execute,
                provider_id=subscription.provider_id,
                provider_merchant_id=subscription.provider_merchant_id,
                provider_subscription_id=subscription.provider_subscription_id,
            )
            is None
        )
        assert_logs_has_no_business_event(logs, "subscription_changed")

    @pytest.mark.asyncio
    async def test_concurrent_replacements_cannot_leave_older_state(self) -> None:
        subscription = make_subscription()
        await domain.save_subscription(subscription, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)
        older = subscription.replace(
            status=SubscriptionStatusId.paused,
            provider_status=ProviderStatus("paused"),
            provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=1),
        )
        newer = subscription.replace(
            status=SubscriptionStatusId.ended,
            provider_status=ProviderStatus("canceled"),
            ends_at=subscription.provider_updated_at + datetime.timedelta(seconds=2),
            provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=2),
        )

        await asyncio.gather(
            domain.save_subscription(older, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID),
            domain.save_subscription(newer, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID),
        )

        assert (
            await operations.load_subscription(
                execute,
                provider_id=subscription.provider_id,
                provider_merchant_id=subscription.provider_merchant_id,
                provider_subscription_id=subscription.provider_subscription_id,
            )
            == newer
        )


class TestGetSubscription:
    @pytest.mark.asyncio
    async def test_returns_exact_snapshot_or_none(self) -> None:
        subscription = make_subscription()
        await domain.save_subscription(subscription, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)

        assert (
            await domain.get_subscription(
                provider_id=subscription.provider_id,
                provider_merchant_id=subscription.provider_merchant_id,
                provider_subscription_id=subscription.provider_subscription_id,
            )
            == subscription
        )
        assert (
            await domain.get_subscription(
                provider_id=subscription.provider_id,
                provider_merchant_id=subscription.provider_merchant_id,
                provider_subscription_id=ProviderSubscriptionId("missing"),
            )
            is None
        )


class TestGetSubscriptionsForUser:
    @pytest.mark.asyncio
    async def test_empty_statuses_returns_empty_list(self) -> None:
        user_id = new_user_id()

        assert await domain.get_subscriptions_for_user(user_id, statuses=[]) == []

    @pytest.mark.asyncio
    async def test_filters_by_statuses(self) -> None:
        user_id = new_user_id()
        active = make_subscription(
            user_id=user_id,
            provider_subscription_id=ProviderSubscriptionId("domain-filter-active"),
        )
        ended = make_subscription(
            user_id=user_id,
            provider_subscription_id=ProviderSubscriptionId("domain-filter-ended"),
            status=SubscriptionStatusId.ended,
        )
        await domain.save_subscription(active, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)
        await domain.save_subscription(ended, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)

        assert await domain.get_subscriptions_for_user(user_id, statuses=[SubscriptionStatusId.ended]) == [ended]

    @pytest.mark.asyncio
    async def test_returns_all_statuses_in_order(self) -> None:
        selected_user_id = new_user_id()
        other_user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        ended = make_subscription(
            user_id=selected_user_id,
            provider_subscription_id=ProviderSubscriptionId("domain-ended"),
            status=SubscriptionStatusId.ended,
            provider_status=ProviderStatus("canceled"),
            started_at=now - datetime.timedelta(days=1),
            ends_at=now,
        )
        active = make_subscription(
            user_id=selected_user_id,
            provider_subscription_id=ProviderSubscriptionId("domain-active"),
            started_at=now,
        )
        other = make_subscription(
            user_id=other_user_id,
            provider_subscription_id=ProviderSubscriptionId("domain-other-user"),
        )
        await domain.save_subscription(ended, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)
        await domain.save_subscription(active, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)
        await domain.save_subscription(other, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("sub_subscriptions"),
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
            provider_subscription_id=ProviderSubscriptionId("domain-alive-without-end"),
            started_at=now,
        )
        alive_until_future = make_subscription(
            user_id=user_id,
            provider_subscription_id=ProviderSubscriptionId("domain-alive-until-future"),
            started_at=now - datetime.timedelta(seconds=1),
            ends_at=now + datetime.timedelta(days=1),
        )
        expired = make_subscription(
            user_id=user_id,
            provider_subscription_id=ProviderSubscriptionId("domain-expired"),
            started_at=now - datetime.timedelta(seconds=2),
            ends_at=now - datetime.timedelta(seconds=1),
        )
        ending_at_request = make_subscription(
            user_id=user_id,
            provider_subscription_id=ProviderSubscriptionId("domain-ending-at-request"),
            started_at=now - datetime.timedelta(seconds=3),
            ends_at=now,
        )
        ended = make_subscription(
            user_id=user_id,
            provider_subscription_id=ProviderSubscriptionId("domain-not-alive"),
            status=SubscriptionStatusId.ended,
            started_at=now - datetime.timedelta(seconds=4),
            ends_at=now + datetime.timedelta(days=1),
        )
        for subscription in (alive_without_end, alive_until_future, expired, ending_at_request, ended):
            await domain.save_subscription(subscription, actor_kind=_ACTOR_KIND, actor_id=_ACTOR_ID)

        assert await domain.get_alive_subscriptions_for_user(user_id) == [alive_without_end, alive_until_future]
