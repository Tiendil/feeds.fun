import datetime
import uuid
from typing import cast

import pytest
from pydantic import ValidationError

from ffun.core.postgresql import execute
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.domain.domain import new_user_id
from ffun.domain.entities import BenefitTransactionId, OneTimePurchaseId, ProviderStatus
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
        one_time_purchase_id = operations.new_purchase_id()
        await operations.insert_provider_purchase_reference(
            execute,
            reference,
            one_time_purchase_id=one_time_purchase_id,
        )

        assert await operations.load_provider_purchase_reference(execute, reference) == one_time_purchase_id


class TestInsertProviderPurchaseReference:
    @pytest.mark.asyncio
    async def test_inserts_reference(self) -> None:
        reference = make_provider_purchase_reference()
        one_time_purchase_id = operations.new_purchase_id()

        async with TableSizeDelta("otp_purchase_refs", delta=1):
            await operations.insert_provider_purchase_reference(
                execute,
                reference,
                one_time_purchase_id=one_time_purchase_id,
            )

        assert await operations.load_provider_purchase_reference(execute, reference) == one_time_purchase_id

    @pytest.mark.asyncio
    async def test_same_mapping_is_no_op(self) -> None:
        reference = make_provider_purchase_reference()
        one_time_purchase_id = operations.new_purchase_id()
        await operations.insert_provider_purchase_reference(
            execute,
            reference,
            one_time_purchase_id=one_time_purchase_id,
        )

        async with TableSizeNotChanged("otp_purchase_refs"):
            await operations.insert_provider_purchase_reference(
                execute,
                reference,
                one_time_purchase_id=one_time_purchase_id,
            )

        assert await operations.load_provider_purchase_reference(execute, reference) == one_time_purchase_id

    @pytest.mark.asyncio
    async def test_different_mapping_fails_without_changing_reference(self) -> None:
        reference = make_provider_purchase_reference()
        stored_purchase_id = operations.new_purchase_id()
        await operations.insert_provider_purchase_reference(
            execute,
            reference,
            one_time_purchase_id=stored_purchase_id,
        )

        async with TableSizeNotChanged("otp_purchase_refs"):
            with pytest.raises(errors.ProviderPurchaseReferenceConflict):
                await operations.insert_provider_purchase_reference(
                    execute,
                    reference,
                    one_time_purchase_id=operations.new_purchase_id(),
                )

        assert await operations.load_provider_purchase_reference(execute, reference) == stored_purchase_id

    @pytest.mark.asyncio
    async def test_same_purchase_different_reference_fails_without_creating_reference(self) -> None:
        one_time_purchase_id = operations.new_purchase_id()
        stored_reference = make_provider_purchase_reference()
        requested_reference = make_provider_purchase_reference()
        await operations.insert_provider_purchase_reference(
            execute,
            stored_reference,
            one_time_purchase_id=one_time_purchase_id,
        )

        async with TableSizeNotChanged("otp_purchase_refs"):
            with pytest.raises(errors.ProviderPurchaseReferenceConflict):
                await operations.insert_provider_purchase_reference(
                    execute,
                    requested_reference,
                    one_time_purchase_id=one_time_purchase_id,
                )

        assert await operations.load_provider_purchase_reference(execute, stored_reference) == one_time_purchase_id
        assert await operations.load_provider_purchase_reference(execute, requested_reference) is None


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
