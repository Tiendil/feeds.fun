import asyncio
import datetime
import uuid
from typing import cast

import pytest
from pydantic import ValidationError
from pytest_mock import MockerFixture

from ffun.core.postgresql import ExecuteType, execute, transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged, assert_pool_capacity_at_least
from ffun.domain.domain import new_user_id
from ffun.domain.entities import BenefitTransactionId, OneTimePurchaseId, ProviderObjectReference, ProviderStatus
from ffun.one_time_purchases import errors, operations
from ffun.one_time_purchases.entities import PurchaseStatus
from ffun.one_time_purchases.tests.make import make_provider_purchase_reference, make_purchase


class TestNewPurchaseId:
    def test_returns_distinct_uuid_identifiers(self) -> None:
        first = operations.new_purchase_id()
        second = operations.new_purchase_id()

        assert isinstance(first, uuid.UUID)
        assert isinstance(second, uuid.UUID)
        assert first != second


class TestRowToPurchase:
    def test_converts_row_and_removes_persistence_timestamps(self) -> None:
        purchase = make_purchase()
        now = datetime.datetime.now(tz=datetime.UTC)
        row = cast(dict[str, object], purchase.model_dump())
        row.update({"created_at": now, "updated_at": now})

        assert operations.row_to_purchase(row) == purchase

    def test_unexpected_field_raises_module_error(self) -> None:
        purchase = make_purchase()
        row = cast(dict[str, object], purchase.model_dump())
        row["unexpected"] = "value"

        with pytest.raises(errors.InvalidStoredPurchase) as exception_info:
            operations.row_to_purchase(row)

        assert isinstance(exception_info.value.__cause__, ValidationError)

    def test_invalid_row_raises_module_error(self) -> None:
        with pytest.raises(errors.InvalidStoredPurchase) as exception_info:
            operations.row_to_purchase({})

        assert isinstance(exception_info.value.__cause__, ValidationError)


class TestLoadPurchase:
    @pytest.mark.asyncio
    async def test_missing(self) -> None:
        purchase = make_purchase()

        assert await operations.load_purchase(execute, purchase.id) is None

    @pytest.mark.asyncio
    async def test_loads_complete_snapshot_for_exact_identity(self) -> None:
        purchase = make_purchase()
        await operations.save_purchase(execute, purchase)

        assert await operations.load_purchase(execute, purchase.id) == purchase
        assert await operations.load_purchase(execute, operations.new_purchase_id()) is None


class TestLoadProviderPurchaseReference:
    @pytest.mark.asyncio
    async def test_missing(self) -> None:
        reference = make_provider_purchase_reference()

        assert await operations.load_provider_purchase_reference(execute, reference) is None

    @pytest.mark.asyncio
    async def test_loads_exact_external_identity(self) -> None:
        reference = make_provider_purchase_reference()
        one_time_purchase_id = await operations.resolve_provider_purchase_reference(execute, reference)

        assert await operations.load_provider_purchase_reference(execute, reference) == one_time_purchase_id


class TestResolveProviderPurchaseReference:
    @pytest.mark.asyncio
    async def test_creates_and_returns_identity(self) -> None:
        reference = make_provider_purchase_reference()

        async with TableSizeDelta("otp_purchase_refs", delta=1):
            one_time_purchase_id = await operations.resolve_provider_purchase_reference(execute, reference)

        assert await operations.load_provider_purchase_reference(execute, reference) == one_time_purchase_id

    @pytest.mark.asyncio
    async def test_returns_existing_identity_without_changes(self) -> None:
        reference = make_provider_purchase_reference()
        one_time_purchase_id = await operations.resolve_provider_purchase_reference(execute, reference)

        async with TableSizeNotChanged("otp_purchase_refs"):
            resolved_purchase_id = await operations.resolve_provider_purchase_reference(execute, reference)

        assert resolved_purchase_id == one_time_purchase_id

    @pytest.mark.asyncio
    async def test_concurrent_creation_converges_on_one_identity(self, mocker: MockerFixture) -> None:
        assert_pool_capacity_at_least(2)
        reference = make_provider_purchase_reference()
        both_initial_loads_finished = asyncio.Event()
        initial_load_count = 0
        original_load = operations.load_provider_purchase_reference

        async def synchronized_load(
            transaction_execute: ExecuteType,
            requested_reference: ProviderObjectReference,
        ) -> OneTimePurchaseId | None:
            nonlocal initial_load_count
            stored_purchase_id = await original_load(transaction_execute, requested_reference)

            if stored_purchase_id is not None:
                return stored_purchase_id

            initial_load_count += 1

            if initial_load_count == 2:
                both_initial_loads_finished.set()

            await both_initial_loads_finished.wait()
            return None

        async def resolve_once() -> OneTimePurchaseId:
            async with transaction() as transaction_execute:
                return await operations.resolve_provider_purchase_reference(transaction_execute, reference)

        mocker.patch.object(operations, "load_provider_purchase_reference", side_effect=synchronized_load)

        async with TableSizeDelta("otp_purchase_refs", delta=1), asyncio.timeout(2):
            first_id, second_id = await asyncio.gather(resolve_once(), resolve_once())

        assert first_id == second_id
        assert await original_load(execute, reference) == first_id


class TestSavePurchase:
    @pytest.mark.asyncio
    async def test_inserts_complete_snapshot(self) -> None:
        purchase = make_purchase()

        async with TableSizeDelta("otp_purchases", delta=1):
            await operations.save_purchase(execute, purchase)

        assert await operations.load_purchase(execute, purchase.id) == purchase

    @pytest.mark.asyncio
    async def test_updates_complete_mutable_snapshot(self) -> None:
        purchase = make_purchase()
        await operations.save_purchase(execute, purchase)
        replacement = purchase.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            status=PurchaseStatus.refunded,
            provider_status=ProviderStatus("refunded"),
            purchased_at=purchase.purchased_at + datetime.timedelta(seconds=1),
            provider_updated_at=purchase.provider_updated_at + datetime.timedelta(seconds=1),
        )

        async with TableSizeNotChanged("otp_purchases"):
            await operations.save_purchase(execute, replacement)

        assert await operations.load_purchase(execute, purchase.id) == replacement

    @pytest.mark.asyncio
    async def test_updates_only_provider_time(self) -> None:
        purchase = make_purchase()
        await operations.save_purchase(execute, purchase)
        advanced = purchase.replace(
            state_transaction_id=BenefitTransactionId(uuid.uuid4()),
            provider_updated_at=purchase.provider_updated_at + datetime.timedelta(seconds=1),
        )

        async with TableSizeNotChanged("otp_purchases"):
            await operations.save_purchase(execute, advanced)

        assert await operations.load_purchase(execute, purchase.id) == advanced


class TestLoadPurchases:
    @pytest.mark.asyncio
    async def test_empty_status_filter(self) -> None:
        assert await operations.load_purchases(execute, new_user_id(), statuses=[]) == []

    @pytest.mark.asyncio
    async def test_unknown_user(self) -> None:
        assert await operations.load_purchases(execute, new_user_id()) == []

    @pytest.mark.asyncio
    async def test_filters_by_statuses(self) -> None:
        user_id = new_user_id()
        completed = make_purchase(user_id=user_id)
        refunded = make_purchase(user_id=user_id, status=PurchaseStatus.refunded)
        await operations.save_purchase(execute, completed)
        await operations.save_purchase(execute, refunded)

        assert await operations.load_purchases(
            execute,
            user_id,
            statuses=[PurchaseStatus.completed],
        ) == [completed]
        assert await operations.load_purchases(execute, user_id, statuses=[]) == []

    @pytest.mark.asyncio
    async def test_loads_selected_users_in_deterministic_order(self) -> None:
        selected_user_id = new_user_id()
        other_user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        earlier = make_purchase(
            one_time_purchase_id=OneTimePurchaseId(uuid.UUID(int=3)),
            user_id=selected_user_id,
            purchased_at=now - datetime.timedelta(days=2),
            status=PurchaseStatus.refunded,
        )
        same_time_later_identity = make_purchase(
            one_time_purchase_id=OneTimePurchaseId(uuid.UUID(int=2)),
            user_id=selected_user_id,
            purchased_at=now,
        )
        same_time_earlier_identity = make_purchase(
            one_time_purchase_id=OneTimePurchaseId(uuid.UUID(int=1)),
            user_id=selected_user_id,
            purchased_at=now,
        )
        other = make_purchase(user_id=other_user_id)
        for purchase in (earlier, same_time_later_identity, same_time_earlier_identity, other):
            await operations.save_purchase(execute, purchase)

        loaded = await operations.load_purchases(execute, selected_user_id)

        assert loaded == [same_time_earlier_identity, same_time_later_identity, earlier]
