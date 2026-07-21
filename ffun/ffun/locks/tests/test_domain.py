import asyncio
import enum
import uuid
from typing import cast

import pytest
import pytest_asyncio
from psycopg.errors import UniqueViolation
from pytest_mock import MockerFixture

from ffun.audit import domain as audit_domain
from ffun.audit.entities import AuditEntityKind, AuditEventName
from ffun.core.postgresql import ExecuteType, execute, transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged, assert_pool_capacity_at_least
from ffun.domain.entities import SerializedId
from ffun.locks import domain as locks_domain
from ffun.locks import errors
from ffun.locks.domain import Lock, locked_transaction
from ffun.locks.entities import LockKind
from ffun.locks.tests.helpers import load_acquisition_rows
from ffun.locks.tests.make import new_lock_kind


class ExampleInt(enum.IntEnum):
    one = 1


class ExampleString(enum.StrEnum):
    source = "source"


@pytest_asyncio.fixture(scope="module", autouse=True)  # type: ignore[misc]
async def concurrency_pool(app: object) -> None:
    assert_pool_capacity_at_least(2)


class TestLock:
    @pytest.mark.parametrize(
        ("argument", "expected"),
        [
            ("source", "source"),
            (ExampleString.source, "source"),
            (1, "1"),
            (-10, "-10"),
            (ExampleInt.one, "1"),
            (uuid.UUID("74d7d6d5-24bc-4d90-bc84-45b5f0146b21"), "74d7d6d5-24bc-4d90-bc84-45b5f0146b21"),
            (True, "true"),
            (False, "false"),
        ],
    )
    def test_canonicalize_argument__supported_value(self, argument: object, expected: str) -> None:
        assert Lock._canonicalize_argument(argument) == expected

    @pytest.mark.parametrize(
        "argument",
        ["", "has space", "has|pipe", "кириллица", 1.5, b"bytes", ["list"]],
        ids=["empty", "space", "pipe", "unicode", "float", "bytes", "list"],
    )
    def test_canonicalize_argument__invalid_value(self, argument: object) -> None:
        with pytest.raises(errors.InvalidLockKey):
            Lock._canonicalize_argument(argument)

    def test_build_identity__joins_argument_boundaries(self) -> None:
        assert Lock._build_identity("test_lock", ("first", 2, True)) == ("test_lock", "first|2|true")

    def test_build_identity__integer_and_string_share_identity(self) -> None:
        assert Lock._build_identity("test_lock", (1,)) == Lock._build_identity("test_lock", ("1",))

    def test_build_identity__allows_no_arguments(self) -> None:
        assert Lock._build_identity("test_lock", ()) == ("test_lock", "")

    @pytest.mark.parametrize(
        "lock_kind",
        ["", "UPPER_CASE", "has-hyphen", "double__underscore", "trailing_", cast(str, 1)],
    )
    def test_build_identity__invalid_kind(self, lock_kind: str) -> None:
        with pytest.raises(errors.InvalidLockKey):
            Lock._build_identity(lock_kind, ())

    def test_build_identity__kind_size_boundaries(self) -> None:
        assert Lock._build_identity("a" * 128, ()) == ("a" * 128, "")

        with pytest.raises(errors.InvalidLockKey):
            Lock._build_identity("a" * 129, ())

    def test_build_identity__key_size_boundaries(self) -> None:
        assert Lock._build_identity("test_lock", ("a" * 1024,)) == ("test_lock", "a" * 1024)

        with pytest.raises(errors.InvalidLockKey):
            Lock._build_identity("test_lock", ("a" * 1025,))

    def test_build_identity__oversized_integer(self) -> None:
        with pytest.raises(errors.InvalidLockKey):
            Lock._build_identity("test_lock", (10**5000,))

    @pytest.mark.asyncio
    async def test_aenter__returns_lock_and_inserts_canonical_identity(self) -> None:
        lock_kind = new_lock_kind()
        lock_key = "source|1|true"

        async with TableSizeNotChanged("lk_locks"):
            async with transaction() as transaction_execute:
                lock = Lock(transaction_execute, lock_kind, "source", 1, True)

                async with lock as acquired_lock:
                    assert acquired_lock is lock
                    assert await load_acquisition_rows(transaction_execute, lock_kind) == [
                        {"lock_kind": lock_kind, "lock_key": lock_key}
                    ]

                assert await load_acquisition_rows(transaction_execute, lock_kind) == []

    @pytest.mark.asyncio
    async def test_aenter__reentrant_identity_raises_invariant_violation(self) -> None:
        lock_kind = new_lock_kind()

        async with TableSizeNotChanged("lk_locks"):
            with pytest.raises(errors.LockInvariantViolation) as exception_info:
                async with transaction() as transaction_execute:
                    async with Lock(transaction_execute, lock_kind, "one"):
                        async with Lock(transaction_execute, lock_kind, "one"):
                            pass

        unique_violation = cast(type[Exception], UniqueViolation)
        assert isinstance(exception_info.value.__cause__, unique_violation)

    @pytest.mark.asyncio
    async def test_aenter__invalid_identity_does_not_access_database(self) -> None:
        lock_kind = new_lock_kind()

        async with TableSizeNotChanged("lk_locks"):
            with pytest.raises(errors.InvalidLockKey):
                async with transaction() as transaction_execute:
                    async with Lock(transaction_execute, lock_kind, "invalid value"):
                        pass

    @pytest.mark.asyncio
    async def test_aexit__propagates_body_exception_and_removes_row(self) -> None:
        class ProtectedOperationError(Exception):
            pass

        lock_kind = new_lock_kind()

        async with TableSizeNotChanged("lk_locks"):
            with pytest.raises(ProtectedOperationError):
                async with transaction() as transaction_execute:
                    async with Lock(transaction_execute, lock_kind, "one"):
                        raise ProtectedOperationError()

        assert await load_acquisition_rows(execute, lock_kind) == []

    @pytest.mark.asyncio
    async def test_aexit__cleanup_failure_preserves_body_exception(self) -> None:
        class ProtectedOperationError(Exception):
            pass

        lock_kind = new_lock_kind()

        async with TableSizeNotChanged("lk_locks"):
            with pytest.raises(ProtectedOperationError) as exception_info:
                async with transaction() as transaction_execute:
                    async with Lock(transaction_execute, lock_kind, "one"):
                        await transaction_execute(
                            """
                            DELETE FROM lk_locks
                            WHERE lock_kind = %(lock_kind)s
                            """,
                            {"lock_kind": lock_kind},  # type: ignore[misc]
                        )
                        raise ProtectedOperationError()

        assert any(note.startswith("Lock cleanup failed:") for note in exception_info.value.__notes__)

    @pytest.mark.asyncio
    async def test_aexit__cleanup_failure_propagates_without_body_exception(self) -> None:
        lock_kind = new_lock_kind()

        async with TableSizeNotChanged("lk_locks"):
            with pytest.raises(errors.LockInvariantViolation):
                async with transaction() as transaction_execute:
                    async with Lock(transaction_execute, lock_kind, "one"):
                        await transaction_execute(
                            """
                            DELETE FROM lk_locks
                            WHERE lock_kind = %(lock_kind)s
                            """,
                            {"lock_kind": lock_kind},  # type: ignore[misc]
                        )

    @pytest.mark.asyncio
    async def test_aexit__before_acquisition_raises(self, mocker: MockerFixture) -> None:
        lock = Lock(cast(ExecuteType, mocker.AsyncMock()), new_lock_kind())

        with pytest.raises(RuntimeError, match="exited before acquisition"):
            await lock.__aexit__(None, None, None)

    @pytest.mark.asyncio
    async def test_aexit__mutex_remains_held_until_transaction_finishes(self) -> None:
        lock_kind = new_lock_kind()
        holder_context_exited = asyncio.Event()
        finish_holder = asyncio.Event()
        waiter_attempting = asyncio.Event()
        waiter_entered = asyncio.Event()

        async def hold_mutex() -> None:
            async with transaction() as transaction_execute:
                async with Lock(transaction_execute, lock_kind, "one"):
                    pass

                holder_context_exited.set()
                await finish_holder.wait()

        async def wait_for_mutex() -> None:
            await holder_context_exited.wait()
            waiter_attempting.set()

            async with locked_transaction(lock_kind, "one"):
                waiter_entered.set()

        async with TableSizeNotChanged("lk_locks"):
            holder_task = asyncio.create_task(hold_mutex())
            await holder_context_exited.wait()
            waiter_task = asyncio.create_task(wait_for_mutex())
            await waiter_attempting.wait()

            try:
                with pytest.raises(TimeoutError):
                    async with asyncio.timeout(0.05):
                        await waiter_entered.wait()
            finally:
                finish_holder.set()
                await asyncio.gather(holder_task, waiter_task)

        assert waiter_entered.is_set()


class TestLockedTransaction:
    @pytest.mark.asyncio
    async def test_invalid_identity_does_not_open_transaction(self, mocker: MockerFixture) -> None:
        transaction_mock = mocker.patch.object(locks_domain, "transaction")

        with pytest.raises(errors.InvalidLockKey):
            async with locked_transaction(LockKind("invalid-kind")):
                pass

        transaction_mock.assert_not_called()

    @pytest.mark.asyncio
    async def test_returns_owned_transaction_execute(self) -> None:
        lock_kind = new_lock_kind()

        async with TableSizeNotChanged("lk_locks"):
            async with locked_transaction(lock_kind, "one") as transaction_execute:
                assert (
                    await transaction_execute(
                        """
                    SELECT 1 AS value
                    """
                    )
                    == [{"value": 1}]
                )

    @pytest.mark.asyncio
    async def test_transaction_failure_propagates(self, mocker: MockerFixture) -> None:
        class TransactionError(Exception):
            pass

        class FailingTransaction:
            async def __aenter__(self) -> ExecuteType:
                raise TransactionError()

            async def __aexit__(
                self,
                exception_type: type[BaseException] | None,
                exception: BaseException | None,
                traceback: object | None,
            ) -> None:
                return None

        mocker.patch.object(locks_domain, "transaction", return_value=FailingTransaction())

        with pytest.raises(TransactionError):
            async with locked_transaction(new_lock_kind(), "one"):
                pass

    @pytest.mark.asyncio
    async def test_lock_failure_closes_transaction(self, mocker: MockerFixture) -> None:
        class AcquisitionError(Exception):
            pass

        mocker.patch.object(locks_domain.operations, "acquire", side_effect=AcquisitionError)

        async with TableSizeNotChanged("lk_locks"):
            with pytest.raises(AcquisitionError):
                async with locked_transaction(new_lock_kind(), "one"):
                    pass

    @pytest.mark.asyncio
    async def test_different_identity_does_not_wait(self) -> None:
        first_lock_kind = new_lock_kind()
        second_lock_kind = new_lock_kind()
        holder_entered = asyncio.Event()
        finish_holder = asyncio.Event()

        async def hold_first_mutex() -> None:
            async with locked_transaction(first_lock_kind, "one"):
                holder_entered.set()
                await finish_holder.wait()

        async with TableSizeNotChanged("lk_locks"):
            holder_task = asyncio.create_task(hold_first_mutex())
            await holder_entered.wait()

            try:
                async with asyncio.timeout(1):
                    async with locked_transaction(second_lock_kind, "one"):
                        pass
            finally:
                finish_holder.set()
                await holder_task

    @pytest.mark.asyncio
    async def test_successful_transaction_allows_waiter_to_enter(self) -> None:
        lock_kind = new_lock_kind()
        holder_entered = asyncio.Event()
        finish_holder = asyncio.Event()
        waiter_attempting = asyncio.Event()
        waiter_entered = asyncio.Event()

        async def hold_mutex() -> None:
            async with locked_transaction(lock_kind, "one"):
                holder_entered.set()
                await finish_holder.wait()

        async def wait_for_mutex() -> None:
            await holder_entered.wait()
            waiter_attempting.set()

            async with locked_transaction(lock_kind, "one"):
                waiter_entered.set()

        async with TableSizeNotChanged("lk_locks"):
            holder_task = asyncio.create_task(hold_mutex())
            await holder_entered.wait()
            waiter_task = asyncio.create_task(wait_for_mutex())
            await waiter_attempting.wait()

            try:
                with pytest.raises(TimeoutError):
                    async with asyncio.timeout(0.05):
                        await waiter_entered.wait()
            finally:
                finish_holder.set()
                await asyncio.gather(holder_task, waiter_task)

        assert waiter_entered.is_set()

    @pytest.mark.asyncio
    async def test_failed_transaction_allows_waiter_to_enter(self) -> None:
        class ProtectedOperationError(Exception):
            pass

        lock_kind = new_lock_kind()
        holder_entered = asyncio.Event()
        fail_holder = asyncio.Event()
        waiter_attempting = asyncio.Event()
        waiter_entered = asyncio.Event()

        async def hold_mutex() -> None:
            with pytest.raises(ProtectedOperationError):
                async with locked_transaction(lock_kind, "one"):
                    holder_entered.set()
                    await fail_holder.wait()
                    raise ProtectedOperationError()

        async def wait_for_mutex() -> None:
            await holder_entered.wait()
            waiter_attempting.set()

            async with locked_transaction(lock_kind, "one"):
                waiter_entered.set()

        async with TableSizeNotChanged("lk_locks"):
            holder_task = asyncio.create_task(hold_mutex())
            await holder_entered.wait()
            waiter_task = asyncio.create_task(wait_for_mutex())
            await waiter_attempting.wait()

            try:
                with pytest.raises(TimeoutError):
                    async with asyncio.timeout(0.05):
                        await waiter_entered.wait()
            finally:
                fail_holder.set()
                await asyncio.gather(holder_task, waiter_task)

        assert waiter_entered.is_set()

    @pytest.mark.asyncio
    async def test_commits_protected_work(self) -> None:
        lock_kind = new_lock_kind()

        async with TableSizeDelta("a_records", delta=1), TableSizeNotChanged("lk_locks"):
            async with locked_transaction(lock_kind, "commit") as transaction_execute:
                record_id = await audit_domain.record(
                    transaction_execute,
                    event=AuditEventName("lock_test_committed"),
                    actor_kind=AuditEntityKind.system,
                    actor_id=SerializedId("system"),
                    subject_kind=AuditEntityKind.system,
                    subject_id=SerializedId("locks"),
                )

        assert (
            await execute(
                """
            SELECT id
            FROM a_records
            WHERE id = %(id)s
            """,
                {"id": record_id},  # type: ignore[misc]
            )
            == [{"id": record_id}]
        )

    @pytest.mark.asyncio
    async def test_rolls_back_protected_work(self) -> None:
        class ProtectedOperationError(Exception):
            pass

        lock_kind = new_lock_kind()
        record_id = None

        async with TableSizeNotChanged("a_records"), TableSizeNotChanged("lk_locks"):
            with pytest.raises(ProtectedOperationError):
                async with locked_transaction(lock_kind, "rollback") as transaction_execute:
                    record_id = await audit_domain.record(
                        transaction_execute,
                        event=AuditEventName("lock_test_rolled_back"),
                        actor_kind=AuditEntityKind.system,
                        actor_id=SerializedId("system"),
                        subject_kind=AuditEntityKind.system,
                        subject_id=SerializedId("locks"),
                    )
                    raise ProtectedOperationError()

        assert record_id is not None
        assert (
            await execute(
                """
                SELECT id
                FROM a_records
                WHERE id = %(id)s
                """,
                {"id": record_id},  # type: ignore[misc]
            )
            == []
        )

    @pytest.mark.asyncio
    async def test_missing_acquisition_row_rolls_back(self) -> None:
        lock_kind = new_lock_kind()

        async with TableSizeNotChanged("a_records"), TableSizeNotChanged("lk_locks"):
            with pytest.raises(errors.LockInvariantViolation):
                async with locked_transaction(lock_kind, "missing") as transaction_execute:
                    await audit_domain.record(
                        transaction_execute,
                        event=AuditEventName("lock_test_missing_row"),
                        actor_kind=AuditEntityKind.system,
                        actor_id=SerializedId("system"),
                        subject_kind=AuditEntityKind.system,
                        subject_id=SerializedId("locks"),
                    )
                    await transaction_execute(
                        """
                        DELETE FROM lk_locks
                        WHERE lock_kind = %(lock_kind)s
                        """,
                        {"lock_kind": lock_kind},  # type: ignore[misc]
                    )
