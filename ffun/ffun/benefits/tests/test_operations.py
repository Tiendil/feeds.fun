import datetime
import uuid
from typing import cast

import pytest
from pydantic import ValidationError

from ffun.benefits import errors, operations
from ffun.benefits.entities import BenefitSourceId, BenefitSourceTransactionId
from ffun.benefits.tests.make import make_benefit_transaction
from ffun.core.postgresql import execute
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged


class TestNewBenefitTransactionId:
    def test_returns_distinct_uuid_identifiers(self) -> None:
        first = operations.new_benefit_transaction_id()
        second = operations.new_benefit_transaction_id()

        assert isinstance(first, uuid.UUID)
        assert isinstance(second, uuid.UUID)
        assert first != second


class TestRowToBenefitTransaction:
    def test_converts_row_and_removes_persistence_timestamp(self) -> None:
        transaction = make_benefit_transaction()
        row = cast(dict[str, object], transaction.model_dump())
        row["created_at"] = datetime.datetime.now(tz=datetime.UTC)
        row["one_time_purchase_id"] = None

        assert operations.row_to_benefit_transaction(row) == transaction

    def test_unexpected_field_raises_module_error(self) -> None:
        transaction = make_benefit_transaction()
        row = cast(dict[str, object], transaction.model_dump())
        row["unexpected"] = "value"

        with pytest.raises(errors.InvalidStoredBenefitTransaction) as exception_info:
            operations.row_to_benefit_transaction(row)

        assert isinstance(exception_info.value.__cause__, ValidationError)

    def test_invalid_row_raises_module_error(self) -> None:
        with pytest.raises(errors.InvalidStoredBenefitTransaction) as exception_info:
            operations.row_to_benefit_transaction({})

        assert isinstance(exception_info.value.__cause__, ValidationError)


class TestSaveBenefitTransaction:
    @pytest.mark.asyncio
    async def test_inserts_complete_transaction(self) -> None:
        transaction = make_benefit_transaction()

        async with TableSizeDelta("b_transactions", delta=1):
            created = await operations.save_benefit_transaction(execute, transaction)

        assert created
        assert await operations.load_benefit_transaction(execute, transaction.id) == transaction
        query_parameters: dict[str, object] = {"transaction_id": transaction.id}
        rows = cast(
            list[dict[str, object]],
            await execute(
                """
                SELECT subscription_id, one_time_purchase_id
                FROM b_transactions
                WHERE id = %(transaction_id)s
                """,
                query_parameters,
            ),
        )
        assert rows == [
            {
                "subscription_id": transaction.subscription_id,
                "one_time_purchase_id": None,
            }
        ]

    @pytest.mark.asyncio
    async def test_duplicate_source_identity_is_no_op(self) -> None:
        first = make_benefit_transaction()
        duplicate = make_benefit_transaction(
            source_id=first.source_id,
            source_transaction_id=first.source_transaction_id,
        )
        assert await operations.save_benefit_transaction(execute, first)

        async with TableSizeNotChanged("b_transactions"):
            created = await operations.save_benefit_transaction(execute, duplicate)

        assert not created
        assert (
            await operations.load_benefit_transaction_by_source(
                execute,
                source_id=first.source_id,
                source_transaction_id=first.source_transaction_id,
            )
            == first
        )


class TestLoadBenefitTransaction:
    @pytest.mark.asyncio
    async def test_missing(self) -> None:
        assert await operations.load_benefit_transaction(execute, operations.new_benefit_transaction_id()) is None

    @pytest.mark.asyncio
    async def test_loads_exact_identity(self) -> None:
        transaction = make_benefit_transaction()
        await operations.save_benefit_transaction(execute, transaction)

        assert await operations.load_benefit_transaction(execute, transaction.id) == transaction


class TestLoadBenefitTransactionBySource:
    @pytest.mark.asyncio
    async def test_missing(self) -> None:
        assert (
            await operations.load_benefit_transaction_by_source(
                execute,
                source_id=BenefitSourceId(21),
                source_transaction_id=BenefitSourceTransactionId(uuid.uuid4()),
            )
            is None
        )

    @pytest.mark.asyncio
    async def test_loads_exact_source_identity(self) -> None:
        transaction = make_benefit_transaction()
        await operations.save_benefit_transaction(execute, transaction)

        assert (
            await operations.load_benefit_transaction_by_source(
                execute,
                source_id=transaction.source_id,
                source_transaction_id=transaction.source_transaction_id,
            )
            == transaction
        )
