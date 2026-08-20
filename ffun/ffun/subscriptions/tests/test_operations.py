import datetime
import uuid
from typing import cast

import pytest
from pydantic import ValidationError

from ffun.core.postgresql import execute
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.domain.domain import new_user_id
from ffun.domain.entities import BenefitId, BenefitTransactionId, SubscriptionId
from ffun.subscriptions import errors, operations
from ffun.subscriptions.entities import SubscriptionStatusId
from ffun.subscriptions.tests.make import make_provider_subscription_reference, make_subscription


class TestNewSubscriptionId:
    def test_returns_distinct_uuid_identifiers(self) -> None:
        first = operations.new_subscription_id()
        second = operations.new_subscription_id()

        assert isinstance(first, uuid.UUID)
        assert isinstance(second, uuid.UUID)
        assert first != second


class TestRowToSubscription:
    def test_converts_row_and_removes_persistence_timestamps(self) -> None:
        subscription = make_subscription()
        now = datetime.datetime.now(tz=datetime.UTC)
        row = cast(dict[str, object], subscription.model_dump())
        row.update({"created_at": now, "updated_at": now})

        assert operations.row_to_subscription(row) == subscription

    def test_unexpected_field_raises_module_error(self) -> None:
        subscription = make_subscription()
        row = cast(dict[str, object], subscription.model_dump())
        row["unexpected"] = "value"

        with pytest.raises(errors.InvalidStoredSubscription) as exception_info:
            operations.row_to_subscription(row)

        assert isinstance(exception_info.value.__cause__, ValidationError)

    def test_invalid_row_raises_module_error(self) -> None:
        with pytest.raises(errors.InvalidStoredSubscription) as exception_info:
            operations.row_to_subscription({})

        assert isinstance(exception_info.value.__cause__, ValidationError)


class TestLoadSubscription:
    @pytest.mark.asyncio
    async def test_missing(self) -> None:
        subscription = make_subscription()

        assert await operations.load_subscription(execute, subscription.id) is None

    @pytest.mark.asyncio
    async def test_loads_complete_snapshot_for_exact_identity(self) -> None:
        subscription = make_subscription()
        await operations.save_subscription(execute, subscription)

        assert await operations.load_subscription(execute, subscription.id) == subscription
        assert await operations.load_subscription(execute, operations.new_subscription_id()) is None


class TestLoadProviderSubscriptionReference:
    @pytest.mark.asyncio
    async def test_missing(self) -> None:
        reference = make_provider_subscription_reference()

        assert await operations.load_provider_subscription_reference(execute, reference) is None

    @pytest.mark.asyncio
    async def test_loads_exact_external_identity(self) -> None:
        reference = make_provider_subscription_reference()
        subscription_id = operations.new_subscription_id()
        await operations.insert_provider_subscription_reference(
            execute,
            reference,
            subscription_id=subscription_id,
        )

        assert await operations.load_provider_subscription_reference(execute, reference) == subscription_id


class TestInsertProviderSubscriptionReference:
    @pytest.mark.asyncio
    async def test_inserts_reference(self) -> None:
        reference = make_provider_subscription_reference()
        subscription_id = operations.new_subscription_id()

        async with TableSizeDelta("sb_subscription_refs", delta=1):
            await operations.insert_provider_subscription_reference(
                execute,
                reference,
                subscription_id=subscription_id,
            )

        assert await operations.load_provider_subscription_reference(execute, reference) == subscription_id

    @pytest.mark.asyncio
    async def test_same_mapping_is_no_op(self) -> None:
        reference = make_provider_subscription_reference()
        subscription_id = operations.new_subscription_id()
        await operations.insert_provider_subscription_reference(
            execute,
            reference,
            subscription_id=subscription_id,
        )

        async with TableSizeNotChanged("sb_subscription_refs"):
            await operations.insert_provider_subscription_reference(
                execute,
                reference,
                subscription_id=subscription_id,
            )

        assert await operations.load_provider_subscription_reference(execute, reference) == subscription_id

    @pytest.mark.asyncio
    async def test_different_mapping_fails_without_changing_reference(self) -> None:
        reference = make_provider_subscription_reference()
        stored_subscription_id = operations.new_subscription_id()
        await operations.insert_provider_subscription_reference(
            execute,
            reference,
            subscription_id=stored_subscription_id,
        )

        async with TableSizeNotChanged("sb_subscription_refs"):
            with pytest.raises(errors.ProviderSubscriptionReferenceConflict):
                await operations.insert_provider_subscription_reference(
                    execute,
                    reference,
                    subscription_id=operations.new_subscription_id(),
                )

        assert await operations.load_provider_subscription_reference(execute, reference) == stored_subscription_id

    @pytest.mark.asyncio
    async def test_same_subscription_different_reference_fails_without_creating_reference(self) -> None:
        subscription_id = operations.new_subscription_id()
        stored_reference = make_provider_subscription_reference()
        requested_reference = make_provider_subscription_reference()
        await operations.insert_provider_subscription_reference(
            execute,
            stored_reference,
            subscription_id=subscription_id,
        )

        async with TableSizeNotChanged("sb_subscription_refs"):
            with pytest.raises(errors.ProviderSubscriptionReferenceConflict):
                await operations.insert_provider_subscription_reference(
                    execute,
                    requested_reference,
                    subscription_id=subscription_id,
                )

        assert await operations.load_provider_subscription_reference(execute, stored_reference) == subscription_id
        assert await operations.load_provider_subscription_reference(execute, requested_reference) is None


class TestSaveSubscription:
    @pytest.mark.asyncio
    async def test_inserts_complete_snapshot(self) -> None:
        subscription = make_subscription(
            expected_renewal_at=datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=30)
        )

        async with TableSizeDelta("sb_subscriptions", delta=1):
            await operations.save_subscription(execute, subscription)

        assert await operations.load_subscription(execute, subscription.id) == subscription

    @pytest.mark.asyncio
    async def test_updates_complete_mutable_snapshot(self) -> None:
        subscription = make_subscription()
        await operations.save_subscription(execute, subscription)
        replacement = subscription.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            benefit_id=BenefitId("replacement-benefit"),
            status=SubscriptionStatusId.ended,
            provider_status="canceled",
            started_at=subscription.started_at + datetime.timedelta(seconds=1),
            ends_at=subscription.provider_updated_at,
            provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=1),
        )

        async with TableSizeNotChanged("sb_subscriptions"):
            await operations.save_subscription(execute, replacement)

        assert await operations.load_subscription(execute, subscription.id) == replacement

    @pytest.mark.asyncio
    async def test_updates_only_provider_time(self) -> None:
        subscription = make_subscription()
        await operations.save_subscription(execute, subscription)
        advanced = subscription.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=1),
        )

        async with TableSizeNotChanged("sb_subscriptions"):
            await operations.save_subscription(execute, advanced)

        assert await operations.load_subscription(execute, subscription.id) == advanced

    @pytest.mark.asyncio
    async def test_does_not_update_immutable_ownership(self) -> None:
        subscription = make_subscription()
        await operations.save_subscription(execute, subscription)
        incoming = subscription.replace(
            user_id=new_user_id(),
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=SubscriptionStatusId.ended,
        )

        async with TableSizeNotChanged("sb_subscriptions"):
            await operations.save_subscription(execute, incoming)

        assert await operations.load_subscription(execute, subscription.id) == incoming.replace(
            user_id=subscription.user_id
        )


class TestLoadSubscriptions:
    @pytest.mark.asyncio
    async def test_empty_filter(self) -> None:
        assert await operations.load_subscriptions(execute, []) == []

    @pytest.mark.asyncio
    async def test_filters_by_statuses(self) -> None:
        user_id = new_user_id()
        active = make_subscription(
            user_id=user_id,
        )
        ended = make_subscription(
            user_id=user_id,
            status=SubscriptionStatusId.ended,
        )
        await operations.save_subscription(execute, active)
        await operations.save_subscription(execute, ended)

        assert await operations.load_subscriptions(
            execute,
            [user_id],
            statuses=[SubscriptionStatusId.active],
        ) == [active]
        assert await operations.load_subscriptions(execute, [user_id], statuses=[]) == []

    @pytest.mark.asyncio
    async def test_loads_selected_users_in_deterministic_order(self) -> None:
        selected_user_id = new_user_id()
        other_user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        earlier = make_subscription(
            subscription_id=SubscriptionId(uuid.UUID(int=3)),
            user_id=selected_user_id,
            started_at=now - datetime.timedelta(days=2),
            status=SubscriptionStatusId.ended,
            ends_at=now - datetime.timedelta(days=1),
        )
        same_start_later_identity = make_subscription(
            subscription_id=SubscriptionId(uuid.UUID(int=2)),
            user_id=selected_user_id,
            started_at=now,
        )
        same_start_earlier_identity = make_subscription(
            subscription_id=SubscriptionId(uuid.UUID(int=1)),
            user_id=selected_user_id,
            started_at=now,
        )
        other = make_subscription(user_id=other_user_id)
        for subscription in (earlier, same_start_later_identity, same_start_earlier_identity, other):
            await operations.save_subscription(execute, subscription)

        loaded = await operations.load_subscriptions(execute, [selected_user_id, selected_user_id])

        assert loaded == [same_start_earlier_identity, same_start_later_identity, earlier]
