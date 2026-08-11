import datetime
from typing import cast

import pytest
from pydantic import ValidationError

from ffun.core.postgresql import execute
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.domain.domain import new_user_id
from ffun.subscriptions import errors, operations
from ffun.subscriptions.entities import ProviderCustomerId, ProviderSubscriptionId, SubscriptionStatusId
from ffun.subscriptions.tests.make import make_subscription


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

        assert (
            await operations.load_subscription(
                execute,
                provider_id=subscription.provider_id,
                provider_merchant_id=subscription.provider_merchant_id,
                provider_subscription_id=subscription.provider_subscription_id,
            )
            is None
        )

    @pytest.mark.asyncio
    async def test_loads_complete_snapshot_for_exact_identity(self) -> None:
        subscription = make_subscription()
        await operations.upsert_subscription(execute, subscription)

        assert (
            await operations.load_subscription(
                execute,
                provider_id=subscription.provider_id,
                provider_merchant_id=subscription.provider_merchant_id,
                provider_subscription_id=subscription.provider_subscription_id,
            )
            == subscription
        )
        assert (
            await operations.load_subscription(
                execute,
                provider_id=subscription.provider_id,
                provider_merchant_id=subscription.provider_merchant_id,
                provider_subscription_id=ProviderSubscriptionId("missing"),
            )
            is None
        )


class TestUpsertSubscription:
    @pytest.mark.asyncio
    async def test_inserts_complete_snapshot(self) -> None:
        subscription = make_subscription(
            renews_at=datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=30)
        )

        async with TableSizeDelta("sub_subscriptions", delta=1):
            await operations.upsert_subscription(execute, subscription)

        assert (
            await operations.load_subscription(
                execute,
                provider_id=subscription.provider_id,
                provider_merchant_id=subscription.provider_merchant_id,
                provider_subscription_id=subscription.provider_subscription_id,
            )
            == subscription
        )

    @pytest.mark.asyncio
    async def test_updates_complete_mutable_snapshot(self) -> None:
        subscription = make_subscription()
        await operations.upsert_subscription(execute, subscription)
        replacement = subscription.replace(
            status=SubscriptionStatusId.ended,
            provider_status="canceled",
            started_at=subscription.started_at + datetime.timedelta(seconds=1),
            ends_at=subscription.provider_updated_at,
            provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=1),
        )

        async with TableSizeNotChanged("sub_subscriptions"):
            await operations.upsert_subscription(execute, replacement)

        assert (
            await operations.load_subscription(
                execute,
                provider_id=subscription.provider_id,
                provider_merchant_id=subscription.provider_merchant_id,
                provider_subscription_id=subscription.provider_subscription_id,
            )
            == replacement
        )

    @pytest.mark.asyncio
    async def test_updates_only_provider_time(self) -> None:
        subscription = make_subscription()
        await operations.upsert_subscription(execute, subscription)
        advanced = subscription.replace(
            provider_updated_at=subscription.provider_updated_at + datetime.timedelta(seconds=1)
        )

        async with TableSizeNotChanged("sub_subscriptions"):
            await operations.upsert_subscription(execute, advanced)

        assert (
            await operations.load_subscription(
                execute,
                provider_id=subscription.provider_id,
                provider_merchant_id=subscription.provider_merchant_id,
                provider_subscription_id=subscription.provider_subscription_id,
            )
            == advanced
        )

    @pytest.mark.asyncio
    async def test_does_not_update_immutable_ownership(self) -> None:
        subscription = make_subscription()
        await operations.upsert_subscription(execute, subscription)
        incoming = subscription.replace(
            user_id=new_user_id(),
            provider_customer_id=ProviderCustomerId("different-customer"),
            status=SubscriptionStatusId.ended,
        )

        async with TableSizeNotChanged("sub_subscriptions"):
            await operations.upsert_subscription(execute, incoming)

        assert await operations.load_subscription(
            execute,
            provider_id=subscription.provider_id,
            provider_merchant_id=subscription.provider_merchant_id,
            provider_subscription_id=subscription.provider_subscription_id,
        ) == incoming.replace(
            user_id=subscription.user_id,
            provider_customer_id=subscription.provider_customer_id,
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
            provider_subscription_id=ProviderSubscriptionId("filter-active"),
        )
        ended = make_subscription(
            user_id=user_id,
            provider_subscription_id=ProviderSubscriptionId("filter-ended"),
            status=SubscriptionStatusId.ended,
        )
        await operations.upsert_subscription(execute, active)
        await operations.upsert_subscription(execute, ended)

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
            user_id=selected_user_id,
            provider_subscription_id=ProviderSubscriptionId("ordered-earlier"),
            started_at=now - datetime.timedelta(days=2),
            status=SubscriptionStatusId.ended,
            ends_at=now - datetime.timedelta(days=1),
        )
        same_start_later_identity = make_subscription(
            user_id=selected_user_id,
            provider_subscription_id=ProviderSubscriptionId("ordered-b"),
            started_at=now,
        )
        same_start_earlier_identity = make_subscription(
            user_id=selected_user_id,
            provider_subscription_id=ProviderSubscriptionId("ordered-a"),
            started_at=now,
        )
        other = make_subscription(user_id=other_user_id)
        for subscription in (earlier, same_start_later_identity, same_start_earlier_identity, other):
            await operations.upsert_subscription(execute, subscription)

        loaded = await operations.load_subscriptions(execute, [selected_user_id, selected_user_id])

        assert loaded == [same_start_earlier_identity, same_start_later_identity, earlier]
