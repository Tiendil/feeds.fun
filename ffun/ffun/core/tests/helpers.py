import copy
import datetime
from collections import Counter
from types import TracebackType
from typing import Any, Callable, MutableMapping, Optional, Type

import pytest

from ffun.core.postgresql import execute

PRODUCER = Callable[[], Any]


class Comparator:
    message = "Error"

    def __init__(
        self,
        producer: PRODUCER,
        message: Optional[str] = None,
        template: str = "{message}: original={old_value}, new={new_value}.",
    ):
        if message is not None:
            self.message = message

        if not callable(producer):
            self.producer = lambda: copy.deepcopy(producer)
        else:
            self.producer = producer  # type: ignore

        self.old_value: Any = None
        self.template = template

    def __enter__(self) -> "Comparator":
        self.old_value = self.producer()  # type: ignore
        return self

    def __exit__(
        self,
        exc_type: Type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        __tracebackhide__ = True  # pylint: disable=W0612

        new_value = self.producer()  # type: ignore

        if self.validate(self.old_value, new_value):
            self.fail(self.old_value, new_value)

    async def __aenter__(self) -> "Comparator":
        self.old_value = await self.producer()  # type: ignore
        return self

    async def __aexit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        __tracebackhide__ = True  # pylint: disable=W0612

        new_value = await self.producer()  # type: ignore

        if self.validate(self.old_value, new_value):
            self.fail(self.old_value, new_value)

    def fail(self, old_value: Any, new_value: Any) -> None:
        pytest.fail(self.template.format(message=self.message, old_value=old_value, new_value=new_value))

    def validate(self, old_value: Any, new_value: Any) -> bool:
        raise NotImplementedError()


class NotChanged(Comparator):
    message = "Value changed"

    def validate(self, old_value: Any, new_value: Any) -> bool:
        return bool(old_value != new_value)


class Changed(Comparator):
    message = "Value has not changed"

    def validate(self, old_value: Any, new_value: Any) -> bool:
        return bool(old_value == new_value)


class Increased(Comparator):
    message = "Value has not increased"

    def validate(self, old_value: Any, new_value: Any) -> bool:
        return bool(old_value < new_value)


class Decreased(Comparator):
    message = "Value has not decreased"

    def validate(self, old_value: Any, new_value: Any) -> bool:
        return bool(old_value < new_value)


class Delta(Comparator):
    def __init__(self, producer: PRODUCER, delta: Any, **kwargs: Any):
        if "message" not in kwargs:
            kwargs["message"] = f"Value has not changed to delta {delta}"

        super().__init__(producer, **kwargs)

        self.delta = delta

    def validate(self, old_value: Any, new_value: Any) -> bool:
        return bool(new_value - old_value != self.delta)


class TableSizeMixin:
    async def _producer(self) -> int:
        results = await execute(f"SELECT count(*) AS number FROM {self.table}")  # type: ignore # noqa: S608
        size = results[0]["number"]
        assert isinstance(size, int)
        return size


class TableSizeDelta(Delta, TableSizeMixin):
    def __init__(self, table: str, **kwargs: Any) -> None:
        if "producer" not in kwargs:
            kwargs["producer"] = self._producer

        super().__init__(**kwargs)

        self.table = table


class TableSizeNotChanged(NotChanged, TableSizeMixin):
    def __init__(self, table: str, **kwargs: Any) -> None:
        if "producer" not in kwargs:
            kwargs["producer"] = self._producer

        super().__init__(**kwargs)

        self.table = table


def assert_times_is_near(
    a: datetime.datetime, b: datetime.datetime, delta: datetime.timedelta = datetime.timedelta(seconds=1)
) -> None:
    assert abs(a - b) < delta


def assert_logs(logs: list[MutableMapping[str, Any]], **kwargs: int) -> None:
    found_enents = Counter(log["event"] for log in logs)

    for key, expected_count in kwargs.items():
        if expected_count != found_enents.get(key, 0):
            pytest.fail(
                f"Key {key} not found {expected_count} times in logs, but found {found_enents.get(key, 0)} times"
            )
