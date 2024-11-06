import contextlib
import copy
import datetime
from collections import Counter
from types import TracebackType
from typing import Any, Callable, Generator, MutableMapping, Optional, Type

import pytest
from structlog import _config as structlog_config
from structlog import contextvars as structlog_contextvars
from structlog.testing import LogCapture
from structlog.types import EventDict

from ffun.core.postgresql import execute
from ffun.domain.entities import UserId

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


class TableSizeDecreased(Decreased, TableSizeMixin):
    def __init__(self, table: str, **kwargs: Any) -> None:
        if "producer" not in kwargs:
            kwargs["producer"] = self._producer

        super().__init__(**kwargs)

        self.table = table


class TableSizeIncreased(Increased, TableSizeMixin):
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


def assert_log_context_vars(**expected: Any) -> None:
    bound_vars = structlog_contextvars.get_contextvars()

    for key, value in expected.items():
        assert bound_vars.get(key) == value, f"Key {key} = {bound_vars} not equal to expected {value}"


def assert_logs_levels(logs: list[MutableMapping[str, Any]], **kwargs: str) -> None:
    for record in logs:
        if record["event"] in kwargs:
            assert record["log_level"] == kwargs[record["event"]], f"Log level is not equal to expected for {record}"


def assert_logs_have_no_errors(logs: list[MutableMapping[str, Any]]) -> None:
    for record in logs:
        if record["log_level"].lower() == "error":
            pytest.fail(f"Error found in logs: {record}")


@contextlib.contextmanager
def capture_logs() -> Generator[list[EventDict], None, None]:
    """
    This is a modified version of capture_logs from structlog.testing

    Differences:

    - merge contextvars
    """
    cap = LogCapture()

    processors = structlog_config.get_config()["processors"]
    old_processors = processors.copy()
    try:
        # clear processors list and use LogCapture for testing
        processors.clear()
        processors.append(structlog_contextvars.merge_contextvars)
        processors.append(cap)
        structlog_config.configure(processors=processors)
        yield cap.entries
    finally:
        # remove LogCapture and restore original processors
        processors.clear()
        processors.extend(old_processors)
        structlog_config.configure(processors=processors)


def assert_logs_has_business_event(  # noqa: CCR001
    logs: list[MutableMapping[str, Any]], name: str, user_id: UserId | None, **atributes: Any
) -> None:

    if user_id is not None:
        user_id = str(user_id)  # type: ignore

    for record in logs:
        if not (record.get("b_kind") == "event" and record["event"] == name and record.get("b_user_id") == user_id):
            continue

        assert "b_uid" in record, "b_uid not found in record"

        for key, value in atributes.items():
            assert key in record["b_attributes"], f"Key {key} not found in record"
            assert (
                record["b_attributes"][key] == value
            ), f"Key {key} = {record["b_attributes"][key]!r} not equal to expected {value!r}"

        break
    else:
        pytest.fail(f"Event {name} not found in logs")


def assert_logs_has_no_business_event(logs: list[MutableMapping[str, Any]], name: str) -> None:
    for record in logs:
        if record.get("b_kind") == "event" and record["event"] == name:
            pytest.fail(f"Event {name} found in logs")
