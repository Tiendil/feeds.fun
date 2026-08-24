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


class TestLoadSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_unsupported_target(self) -> None:
        with pytest.raises(NotImplementedError, match="Unsupported subscription target"):
            await target_resolution._load_subscription_target(object(), execute)


class TestLoadInternalSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_preserves_identity(self) -> None:
        subscription_id = subscription_domain.new_subscription_id()

        assert (
            await target_resolution._load_subscription_target(
                InternalTarget(internal_id=subscription_id),
                execute,
            )
            == subscription_id
        )


class TestLoadExternalSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_unknown_target_has_no_identity(self) -> None:
        assert await target_resolution._load_subscription_target(make_external_target(), execute) is None

    @pytest.mark.asyncio
    async def test_returns_stored_identity(self) -> None:
        target = make_external_target()
        subscription_id = subscription_domain.new_subscription_id()
        await subscription_domain.insert_provider_subscription_reference(
            execute,
            target.provider_reference,
            subscription_id=subscription_id,
        )

        assert await target_resolution._load_subscription_target(target, execute) == subscription_id


class TestLoadNewSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_has_no_identity(self) -> None:
        assert await target_resolution._load_subscription_target(NewTarget(), execute) is None


class TestResolveSubscriptionTarget:
    @pytest.mark.asyncio
    async def test_preserves_internal_identity(self) -> None:
        subscription_id = subscription_domain.new_subscription_id()

        assert (
            await target_resolution.resolve_subscription_target(
                execute,
                InternalTarget(internal_id=subscription_id),
            )
            == subscription_id
        )

    @pytest.mark.asyncio
    async def test_generates_identity_for_new_target(self) -> None:
        subscription_id = await target_resolution.resolve_subscription_target(execute, NewTarget())

        assert isinstance(subscription_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_creates_and_reuses_external_reference(self) -> None:
        target = make_external_target()

        async with TableSizeDelta("sb_subscription_refs", delta=1):
            first_id = await target_resolution.resolve_subscription_target(execute, target)

        async with TableSizeNotChanged("sb_subscription_refs"):
            second_id = await target_resolution.resolve_subscription_target(execute, target)

        assert second_id == first_id
        assert (
            await subscription_domain.load_provider_subscription_reference(execute, target.provider_reference)
            == first_id
        )


class TestLoadOneTimePurchaseTarget:
    @pytest.mark.asyncio
    async def test_unsupported_target(self) -> None:
        with pytest.raises(NotImplementedError, match="Unsupported one-time purchase target"):
            await target_resolution._load_one_time_purchase_target(object(), execute)


class TestLoadInternalOneTimePurchaseTarget:
    @pytest.mark.asyncio
    async def test_preserves_identity(self) -> None:
        one_time_purchase_id = purchase_domain.new_purchase_id()

        assert (
            await target_resolution._load_one_time_purchase_target(
                InternalTarget(internal_id=one_time_purchase_id),
                execute,
            )
            == one_time_purchase_id
        )


class TestLoadExternalOneTimePurchaseTarget:
    @pytest.mark.asyncio
    async def test_unknown_target_has_no_identity(self) -> None:
        target = make_external_target(make_provider_purchase_reference())

        assert await target_resolution._load_one_time_purchase_target(target, execute) is None

    @pytest.mark.asyncio
    async def test_returns_stored_identity(self) -> None:
        target = make_external_target(make_provider_purchase_reference())
        one_time_purchase_id = purchase_domain.new_purchase_id()
        await purchase_domain.save_provider_purchase_reference(
            execute,
            target.provider_reference,
            one_time_purchase_id=one_time_purchase_id,
        )

        assert await target_resolution._load_one_time_purchase_target(target, execute) == one_time_purchase_id


class TestLoadNewOneTimePurchaseTarget:
    @pytest.mark.asyncio
    async def test_has_no_identity(self) -> None:
        assert await target_resolution._load_one_time_purchase_target(NewTarget(), execute) is None


class TestResolveOneTimePurchaseTarget:
    @pytest.mark.asyncio
    async def test_preserves_internal_identity(self) -> None:
        one_time_purchase_id = purchase_domain.new_purchase_id()

        assert (
            await target_resolution.resolve_one_time_purchase_target(
                execute,
                InternalTarget(internal_id=one_time_purchase_id),
            )
            == one_time_purchase_id
        )

    @pytest.mark.asyncio
    async def test_generates_identity_for_new_target(self) -> None:
        one_time_purchase_id = await target_resolution.resolve_one_time_purchase_target(execute, NewTarget())

        assert isinstance(one_time_purchase_id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_creates_and_reuses_external_reference(self) -> None:
        target = make_external_target(make_provider_purchase_reference())

        async with TableSizeDelta("otp_purchase_refs", delta=1):
            first_id = await target_resolution.resolve_one_time_purchase_target(execute, target)

        async with TableSizeNotChanged("otp_purchase_refs"):
            second_id = await target_resolution.resolve_one_time_purchase_target(execute, target)

        assert second_id == first_id
        assert await purchase_domain.load_provider_purchase_reference(execute, target.provider_reference) == first_id
