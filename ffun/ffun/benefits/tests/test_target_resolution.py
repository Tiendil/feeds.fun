import uuid

import pytest

from ffun.benefits import target_resolution
from ffun.benefits.entities import InternalTarget, NewTarget
from ffun.benefits.tests.make import make_external_target
from ffun.core.postgresql import execute
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.one_time_purchases import domain as purchase_domain
from ffun.one_time_purchases.tests.make import make_provider_purchase_reference
from ffun.subscriptions import domain as subscription_domain


class TestResolveSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_unsupported_target(self) -> None:
        with pytest.raises(NotImplementedError, match="Unsupported subscription target"):
            await target_resolution.resolve_subscription_target(object(), execute)

    @pytest.mark.asyncio
    async def test_preserves_internal_identity(self) -> None:
        subscription_id = subscription_domain.new_subscription_id()

        assert (
            await target_resolution.resolve_subscription_target(
                InternalTarget(internal_id=subscription_id),
                execute,
            )
            == subscription_id
        )

    @pytest.mark.asyncio
    async def test_generates_identity_for_new_target(self) -> None:
        subscription_id = await target_resolution.resolve_subscription_target(NewTarget(), execute)

        assert isinstance(subscription_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_creates_and_reuses_external_reference(self) -> None:
        target = make_external_target()

        async with TableSizeDelta("sb_subscription_refs", delta=1):
            first_id = await target_resolution.resolve_subscription_target(target, execute)

        async with TableSizeNotChanged("sb_subscription_refs"):
            second_id = await target_resolution.resolve_subscription_target(target, execute)

        assert second_id == first_id
        assert (
            await subscription_domain.load_provider_subscription_reference(execute, target.provider_reference)
            == first_id
        )


class TestResolveOneTimePurchaseTarget:
    @pytest.mark.asyncio
    async def test_unsupported_target(self) -> None:
        with pytest.raises(NotImplementedError, match="Unsupported one-time purchase target"):
            await target_resolution.resolve_one_time_purchase_target(object(), execute)

    @pytest.mark.asyncio
    async def test_preserves_internal_identity(self) -> None:
        one_time_purchase_id = purchase_domain.new_purchase_id()

        assert (
            await target_resolution.resolve_one_time_purchase_target(
                InternalTarget(internal_id=one_time_purchase_id),
                execute,
            )
            == one_time_purchase_id
        )

    @pytest.mark.asyncio
    async def test_generates_identity_for_new_target(self) -> None:
        one_time_purchase_id = await target_resolution.resolve_one_time_purchase_target(NewTarget(), execute)

        assert isinstance(one_time_purchase_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_creates_and_reuses_external_reference(self) -> None:
        target = make_external_target(make_provider_purchase_reference())

        async with TableSizeDelta("otp_purchase_refs", delta=1):
            first_id = await target_resolution.resolve_one_time_purchase_target(target, execute)

        async with TableSizeNotChanged("otp_purchase_refs"):
            second_id = await target_resolution.resolve_one_time_purchase_target(target, execute)

        assert second_id == first_id
        assert await purchase_domain.load_provider_purchase_reference(execute, target.provider_reference) == first_id
