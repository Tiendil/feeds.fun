import contextlib
import copy
import datetime
from collections import Counter
from types import TracebackType
from typing import Callable, Generator, MutableMapping, Optional, Type
from xml.dom import minidom  # noqa: S408

import pytest
from structlog import _config as structlog_config
from structlog import contextvars as structlog_contextvars
from structlog.testing import LogCapture
from structlog.types import EventDict

from ffun.core.postgresql import execute
from ffun.domain.entities import UserId

PRODUCER = Callable[[], object]


class Comparator:
    message = "Error"

    def __init__(
        self,
        producer: PRODUCER,
        message: Optional[str] = None,
        template: str = "{message}: original={old_value}, new={new_value}.",
    ) -> None:
        if message is not None:
            self.message = message

        if not callable(producer):
            self.producer = lambda: copy.deepcopy(producer)
        else:
            self.producer = producer  # type: ignore

        self.old_value: object = None
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

        if self.validate(self.old_value, new_value):  # type: ignore
            self.fail(self.old_value, new_value)  # type: ignore

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

        if self.validate(self.old_value, new_value):  # type: ignore
            self.fail(self.old_value, new_value)  # type: ignore

    def fail(self, old_value: object, new_value: object) -> None:
        pytest.fail(self.template.format(message=self.message, old_value=old_value, new_value=new_value))

    def validate(self, old_value: object, new_value: object) -> bool:
        raise NotImplementedError()


class NotChanged(Comparator):
    message = "Value changed"

    def validate(self, old_value: object, new_value: object) -> bool:
        return bool(old_value != new_value)


class Changed(Comparator):
    message = "Value has not changed"

    def validate(self, old_value: object, new_value: object) -> bool:
        return bool(old_value == new_value)


class Increased(Comparator):
    message = "Value has not increased"

    def validate(self, old_value: object, new_value: object) -> bool:
        return bool(old_value < new_value)  # type: ignore


class Decreased(Comparator):
    message = "Value has not decreased"

    def validate(self, old_value: object, new_value: object) -> bool:
        return bool(old_value < new_value)  # type: ignore


class Delta(Comparator):
    def __init__(self, producer: PRODUCER, delta: object, **kwargs: object) -> None:
        if "message" not in kwargs:
            kwargs["message"] = f"Value has not changed to delta {delta}"

        super().__init__(producer, **kwargs)  # type: ignore

        self.delta = delta

    def validate(self, old_value: object, new_value: object) -> bool:
        return bool(new_value - old_value != self.delta)  # type: ignore


class TableSizeMixin:
    async def _producer(self) -> int:
        results = await execute(f"SELECT count(*) AS number FROM {self.table}")  # type: ignore # noqa: S608
        size = results[0]["number"]
        assert isinstance(size, int)
        return size


class TableSizeDelta(Delta, TableSizeMixin):
    def __init__(self, table: str, **kwargs: object) -> None:
        if "producer" not in kwargs:
            kwargs["producer"] = self._producer

        super().__init__(**kwargs)  # type: ignore

        self.table = table


class TableSizeNotChanged(NotChanged, TableSizeMixin):
    def __init__(self, table: str, **kwargs: object) -> None:
        if "producer" not in kwargs:
            kwargs["producer"] = self._producer

        super().__init__(**kwargs)  # type: ignore

        self.table = table


class TableSizeDecreased(Decreased, TableSizeMixin):
    def __init__(self, table: str, **kwargs: object) -> None:
        if "producer" not in kwargs:
            kwargs["producer"] = self._producer

        super().__init__(**kwargs)  # type: ignore

        self.table = table


class TableSizeIncreased(Increased, TableSizeMixin):
    def __init__(self, table: str, **kwargs: object) -> None:
        if "producer" not in kwargs:
            kwargs["producer"] = self._producer

        super().__init__(**kwargs)  # type: ignore

        self.table = table


def assert_times_is_near(
    a: datetime.datetime, b: datetime.datetime, delta: datetime.timedelta = datetime.timedelta(seconds=1)
) -> None:
    assert abs(a - b) < delta


def assert_logs(logs: list[MutableMapping[str, object]], **kwargs: int) -> None:
    found_enents = Counter(log["event"] for log in logs)

    for key, expected_count in kwargs.items():
        if expected_count != found_enents.get(key, 0):
            pytest.fail(
                f"Key {key} not found {expected_count} times in logs, but found {found_enents.get(key, 0)} times"
            )


def assert_log_context_vars(**expected: object) -> None:
    bound_vars = structlog_contextvars.get_contextvars()  # type: ignore

    for key, value in expected.items():
        assert bound_vars.get(key) == value, f"Key {key} = {bound_vars} not equal to expected {value}"  # type: ignore


def assert_logs_levels(logs: list[MutableMapping[str, object]], **kwargs: str) -> None:
    for record in logs:
        if record["event"] in kwargs:
            assert record["log_level"] == kwargs[record["event"]], (  # type: ignore
                f"Log level is not equal to expected for {record}"
            )


def assert_logs_have_no_errors(logs: list[MutableMapping[str, object]]) -> None:
    for record in logs:
        if record["log_level"].lower() == "error":  # type: ignore
            pytest.fail(f"Error found in logs: {record}")


@contextlib.contextmanager
def capture_logs() -> Generator[list[EventDict], None, None]:
    """
    This is a modified version of capture_logs from structlog.testing

    Differences:

    - merge contextvars
    """
    cap = LogCapture()

    processors = structlog_config.get_config()["processors"]  # type: ignore
    old_processors = processors.copy()  # type: ignore
    try:
        # clear processors list and use LogCapture for testing
        processors.clear()  # type: ignore
        processors.append(structlog_contextvars.merge_contextvars)  # type: ignore
        processors.append(cap)  # type: ignore
        structlog_config.configure(processors=processors)  # type: ignore
        yield cap.entries
    finally:
        # remove LogCapture and restore original processors
        processors.clear()  # type: ignore
        processors.extend(old_processors)  # type: ignore
        structlog_config.configure(processors=processors)  # type: ignore


def assert_logs_has_business_event(  # noqa: CCR001
    logs: list[MutableMapping[str, object]],
    name: str,
    user_id: UserId | None,
    b_kind: str = "event",
    **attributes: object,
) -> None:

    if user_id is not None:
        user_id = str(user_id)  # type: ignore

    for record in logs:
        if not (record.get("b_kind") == b_kind and record["event"] == name and record.get("b_user_id") == user_id):
            continue

        assert "b_uid" in record, "b_uid not found in record"

        for key, value in attributes.items():
            assert key in record["b_attributes"], f"Key {key} not found in record"  # type: ignore
            assert (
                record["b_attributes"][key] == value  # type: ignore
            ), f"Key {key} = {record["b_attributes"][key]!r} not equal to expected {value!r}"  # type: ignore

        break
    else:
        pytest.fail(f"Event {name} not found in logs")


def assert_logs_has_no_business_event(
    logs: list[MutableMapping[str, object]], name: str, b_kind: str = "event"
) -> None:
    for record in logs:
        if record.get("b_kind") == b_kind and record["event"] == name:
            pytest.fail(f"Event {name} found in logs")


def assert_logs_has_business_slice(*args: object, **kwargs: object) -> None:
    assert "b_kind" not in kwargs, "b_kind should not be passed to assert_logs_has_business_slice"
    kwargs["b_kind"] = "slice"
    assert_logs_has_business_event(*args, **kwargs)  # type: ignore


def assert_logs_has_no_business_slice(*args: object, **kwargs: object) -> None:
    assert "b_kind" not in kwargs, "b_kind should not be passed to assert_logs_has_business_slice"
    kwargs["b_kind"] = "slice"
    assert_logs_has_no_business_event(*args, **kwargs)  # type: ignore


def assert_compare_xml(a: str, b: str) -> None:
    assert minidom.parseString(a).toprettyxml() == minidom.parseString(b).toprettyxml()  # noqa: S318
