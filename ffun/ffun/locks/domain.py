import contextlib
import re
import uuid
from collections.abc import AsyncIterator
from types import TracebackType

from ffun.core.postgresql import ExecuteType, transaction
from ffun.locks import errors, operations
from ffun.locks.entities import LockKind

_LOCK_KIND_PATTERN = re.compile(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*")
_LOCK_ARGUMENT_PATTERN = re.compile(r"[A-Za-z0-9._:@/-]+")
_LOCK_KIND_MAX_BYTES = 128
_LOCK_KEY_MAX_BYTES = 1024


class Lock:
    __slots__ = ("_execute", "_raw_lock_kind", "_lock_arguments", "_acquired_identity")

    def __init__(self, execute: ExecuteType, lock_kind: LockKind, *lock_arguments: object) -> None:
        self._execute = execute
        self._raw_lock_kind = lock_kind
        self._lock_arguments = lock_arguments
        self._acquired_identity: tuple[str, str] | None = None

    @staticmethod
    def _canonicalize_argument(argument: object) -> str:  # noqa: CCR001
        if isinstance(argument, bool):
            value = "true" if argument else "false"
        elif isinstance(argument, int):
            try:
                value = str(int(argument))
            except ValueError as exception:
                raise errors.InvalidLockKey(reason="integer lock argument exceeds the supported size") from exception
        elif isinstance(argument, uuid.UUID):
            value = str(argument)
        elif isinstance(argument, str):
            value = str(argument)
        else:
            raise errors.InvalidLockKey(reason=f"unsupported lock argument type: {type(argument).__name__}")

        if _LOCK_ARGUMENT_PATTERN.fullmatch(value) is None:
            raise errors.InvalidLockKey(
                reason="lock arguments must be non-empty and contain only supported ASCII characters"
            )

        return value

    @classmethod
    def _build_identity(cls, lock_kind: str, lock_arguments: tuple[object, ...]) -> tuple[str, str]:
        if not isinstance(lock_kind, str) or _LOCK_KIND_PATTERN.fullmatch(lock_kind) is None:
            raise errors.InvalidLockKey(reason="lock kind must be a non-empty lowercase snake_case string")

        if len(lock_kind.encode("utf-8")) > _LOCK_KIND_MAX_BYTES:
            raise errors.InvalidLockKey(reason=f"lock kind must not exceed {_LOCK_KIND_MAX_BYTES} bytes")

        lock_key = "|".join(cls._canonicalize_argument(argument) for argument in lock_arguments)

        if len(lock_key.encode("utf-8")) > _LOCK_KEY_MAX_BYTES:
            raise errors.InvalidLockKey(reason=f"lock key must not exceed {_LOCK_KEY_MAX_BYTES} bytes")

        return lock_kind, lock_key

    async def __aenter__(self) -> "Lock":
        lock_kind, lock_key = self._build_identity(self._raw_lock_kind, self._lock_arguments)
        await operations.acquire(self._execute, lock_kind, lock_key)
        self._acquired_identity = (lock_kind, lock_key)
        return self

    async def __aexit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool:
        if self._acquired_identity is None:
            raise RuntimeError("Lock context exited before acquisition")

        lock_kind, lock_key = self._acquired_identity

        try:
            await operations.release(self._execute, lock_kind, lock_key)
        except BaseException as cleanup_exception:
            if exception is None:
                raise

            exception.add_note(f"Lock cleanup failed: {cleanup_exception!r}")
        finally:
            self._acquired_identity = None

        return False


@contextlib.asynccontextmanager
async def locked_transaction(lock_kind: LockKind, *lock_arguments: object) -> AsyncIterator[ExecuteType]:
    Lock._build_identity(lock_kind, lock_arguments)

    async with transaction() as execute:
        async with Lock(execute, lock_kind, *lock_arguments):
            yield execute
