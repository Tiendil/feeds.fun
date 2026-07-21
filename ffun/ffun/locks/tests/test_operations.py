from typing import cast

import pytest
from psycopg.errors import UniqueViolation

from ffun.core.postgresql import execute, transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.locks import errors, operations
from ffun.locks.tests.helpers import count_acquisition_rows, load_acquisition_rows
from ffun.locks.tests.make import new_lock_kind


class TestAcquire:
    @pytest.mark.asyncio
    async def test_inserts_acquisition_row_until_transaction_rolls_back(self) -> None:
        class RollbackTestTransaction(Exception):
            pass

        lock_kind = new_lock_kind()

        async with TableSizeNotChanged("lk_locks"):
            with pytest.raises(RollbackTestTransaction):
                async with transaction() as transaction_execute:
                    async with TableSizeDelta(
                        "lk_locks",
                        delta=1,
                        producer=lambda: count_acquisition_rows(transaction_execute),
                    ):
                        await operations.acquire(transaction_execute, lock_kind, "one")

                    assert await load_acquisition_rows(transaction_execute, lock_kind) == [
                        {"lock_kind": lock_kind, "lock_key": "one"}
                    ]
                    raise RollbackTestTransaction()

        assert await load_acquisition_rows(execute, lock_kind) == []

    @pytest.mark.asyncio
    async def test_committed_row_raises_invariant_violation(self) -> None:
        lock_kind = new_lock_kind()

        async with TableSizeDelta("lk_locks", delta=1):
            await execute(
                """
                INSERT INTO lk_locks (lock_kind, lock_key)
                VALUES (%(lock_kind)s, %(lock_key)s)
                """,
                {"lock_kind": lock_kind, "lock_key": "committed"},  # type: ignore[misc]
            )

        async with TableSizeNotChanged("lk_locks"):
            with pytest.raises(errors.LockInvariantViolation) as exception_info:
                async with transaction() as transaction_execute:
                    await operations.acquire(transaction_execute, lock_kind, "committed")

        unique_violation = cast(type[Exception], UniqueViolation)
        assert isinstance(exception_info.value.__cause__, unique_violation)


class TestRelease:
    @pytest.mark.asyncio
    async def test_deletes_acquisition_row(self) -> None:
        lock_kind = new_lock_kind()

        async with transaction() as transaction_execute:
            await operations.acquire(transaction_execute, lock_kind, "one")

            assert await load_acquisition_rows(transaction_execute, lock_kind) == [
                {"lock_kind": lock_kind, "lock_key": "one"}
            ]

            async with TableSizeDelta(
                "lk_locks",
                delta=-1,
                producer=lambda: count_acquisition_rows(transaction_execute),
            ):
                await operations.release(transaction_execute, lock_kind, "one")

            assert await load_acquisition_rows(transaction_execute, lock_kind) == []

    @pytest.mark.asyncio
    async def test_missing_row_raises_invariant_violation(self) -> None:
        lock_kind = new_lock_kind()

        async with TableSizeNotChanged("lk_locks"):
            with pytest.raises(errors.LockInvariantViolation):
                async with transaction() as transaction_execute:
                    await operations.release(transaction_execute, lock_kind, "missing")
