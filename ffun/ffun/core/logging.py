import contextlib
import copy
import datetime
import enum
import functools
import inspect
import logging
import sys
import time
import uuid
from collections import abc
from typing import Callable, ContextManager, Iterable, Iterator, Protocol, TypeVar, overload, ParamSpec, TypeAlias, cast
from collections.abc import Awaitable, Callable

import pydantic_settings
import structlog
from sentry_sdk import capture_exception, capture_message
from structlog import contextvars as structlog_contextvars

from ffun.core import errors
from ffun.domain.entities import UserId

LabelValue = int | str | None


class Renderer(str, enum.Enum):
    console = "console"
    json = "json"


class Settings(pydantic_settings.BaseSettings):
    level: str = "INFO"
    renderer: Renderer = Renderer.console

    model_config = pydantic_settings.SettingsConfigDict(
        env_nested_delimiter="__", env_file=".env", env_prefix="FFUN_LOGS_", extra="allow"
    )

    @property
    def structlog_level(self) -> int:
        return getattr(logging, self.level.upper())  # type: ignore


settings = Settings()


class LogProcessorType(Protocol):
    async def __call__(self, _: object, __: object, event_dict: dict[str, object]) -> dict[str, object]:
        pass


class Formatter:
    __slots__ = ()

    def can_format(self, value: object) -> bool:
        raise NotImplementedError('You must implement "can_format" in child class')

    def format(self, value: object) -> str:
        raise NotImplementedError('You must implement "format" in child class')


class DateFormatter(Formatter):
    __slots__ = ()

    def can_format(self, value: object) -> bool:
        return isinstance(value, (datetime.date, datetime.datetime))

    def format(self, value: object) -> str:
        assert isinstance(value, (datetime.date, datetime.datetime))
        return value.isoformat()


class UUIDFormatter(Formatter):
    __slots__ = ()

    def can_format(self, value: object) -> bool:
        return isinstance(value, uuid.UUID)

    def format(self, value: object) -> str:
        assert isinstance(value, uuid.UUID)
        return str(value)


class EnumFormatter(Formatter):
    __slots__ = ()

    def can_format(self, value: object) -> bool:
        return isinstance(value, enum.Enum)

    def format(self, value: object) -> str:
        assert isinstance(value, enum.Enum)
        return value.name


class ProcessorFormatter:
    __slots__ = ("_formatters",)

    def __init__(self, formatters: Iterable[Formatter]) -> None:
        self._formatters = list(formatters)

    def __call__(self, _: object, __: object, event_dict: dict[str, object]) -> dict[str, object]:
        for key, value in event_dict.items():
            for formatter in self._formatters:
                if formatter.can_format(value):
                    event_dict[key] = formatter.format(value)
                    break

        return event_dict


def info_extracter(_: object, __: object, event_dict: dict[str, object]) -> dict[str, object]:
    replaced = False

    for key, value in list(event_dict.items()):
        if not hasattr(value, "log_info"):
            continue

        for k, v in value.log_info().items():  # type: ignore
            event_dict[f"{key}_{k}"] = v  # type: ignore

        del event_dict[key]

        replaced = True

    if not replaced:
        return event_dict

    return info_extracter(_, __, event_dict)


def create_formatter() -> ProcessorFormatter:
    formatters = [DateFormatter(), UUIDFormatter(), EnumFormatter()]
    return ProcessorFormatter(formatters)


def log_errors_to_sentry(_: object, __: object, event_dict: dict[str, object]) -> dict[str, object]:
    if event_dict.get("sentry_skip"):
        return event_dict

    level = event_dict.get("level", "")

    assert isinstance(level, str)

    if level.upper() != "ERROR":
        return event_dict

    if event_dict.get("exc_info"):
        capture_exception(sys.exc_info())
    else:
        description = event_dict["event"]
        assert isinstance(description, str)
        capture_message(description)

    return event_dict


def processors_list(use_sentry: bool) -> list[LogProcessorType]:
    sentry_processor = None

    if use_sentry:
        sentry_processor = log_errors_to_sentry

    processors_list = [
        structlog.contextvars.merge_contextvars,
        info_extracter,
        structlog.processors.add_log_level,  # type: ignore
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        sentry_processor,
        structlog.processors.TimeStamper(fmt="ISO", utc=True, key="timestamp"),
        create_formatter(),
        structlog.dev.ConsoleRenderer() if settings.renderer == Renderer.console else None,
        structlog.processors.JSONRenderer() if settings.renderer == Renderer.json else None,
    ]

    return [p for p in processors_list if p is not None]  # type: ignore


class FFunBoundLogger(structlog.typing.FilteringBoundLogger):
    def measure(self, event: str, value: float | int, **labels: LabelValue) -> None:
        pass

    def measure_block_time(  # type: ignore
        self, event: str, **labels: LabelValue
    ) -> ContextManager[dict[str, LabelValue]]:
        pass

    def _normalize_value(self, value: object) -> object:
        pass

    def business_event(self, event: str, user_id: UserId | None, **attributes: object) -> object:
        pass

    def business_slice(self, event: str, user_id: UserId | None, **attributes: LabelValue) -> object:
        pass


class MeasuringBoundLoggerMixin:
    """We extend a logger class with additional metrics logic.

    This mixin is required to work with metrics in 100% the same way as with logs.

    By calling `logging.measure(...)` and other methods, we guarantee that metrics will have the exact attributes
    as expected from log messages (both custom and general like "module"), so the third-party software
    would be able to filter/process messages universally.
    """

    def measure(self, event: str, value: float | int, **labels: LabelValue) -> object:
        if not labels:
            return self.info(event, m_kind="measure", m_value=value)  # type: ignore

        with bound_measure_labels(**labels):
            return self.info(event, m_kind="measure", m_value=value)  # type: ignore

    @contextlib.contextmanager
    def measure_block_time(self, event: str, **labels: LabelValue) -> Iterator[dict[str, LabelValue]]:
        started_at = time.monotonic()

        extra_labels: dict[str, LabelValue] = {}

        with bound_measure_labels(**labels):
            try:
                yield extra_labels
            finally:
                self.measure(event, time.monotonic() - started_at, **extra_labels)


class BusinessBoundLoggerMixin:
    """We extend a logger class with additional business events logic.

    This mixin is required to work with business events in 100% the same way as with logs.
    """

    def _normalize_value(self, value: object) -> object:
        if value is None:
            return None

        if isinstance(value, (int, str, float)):
            return value

        if isinstance(value, abc.Mapping):
            return {str(k): self._normalize_value(v) for k, v in value.items()}

        if isinstance(value, abc.Sequence):
            return [self._normalize_value(v) for v in value]

        return str(value)

    def business_event(self, event: str, user_id: UserId | None, **attributes: LabelValue) -> object:
        return self.info(  # type: ignore
            event,
            b_kind="event",
            b_user_id=str(user_id) if user_id is not None else None,
            b_uid=str(uuid.uuid4()),
            b_attributes=self._normalize_value(attributes),
        )

    # TODO: test
    def business_slice(self, event: str, user_id: UserId | None, **attributes: LabelValue) -> object:
        return self.info(  # type: ignore
            event,
            b_kind="slice",
            b_user_id=str(user_id) if user_id is not None else None,
            b_uid=str(uuid.uuid4()),
            b_attributes=self._normalize_value(attributes),
        )


def make_measuring_bound_logger(level: int) -> type[FFunBoundLogger]:
    filtering_logger_class = structlog.make_filtering_bound_logger(level)

    class _FFunBoundLogger(
        MeasuringBoundLoggerMixin, BusinessBoundLoggerMixin, filtering_logger_class  # type: ignore
    ):
        pass

    return _FFunBoundLogger


def initialize(use_sentry: bool) -> None:
    structlog.configure(
        processors=processors_list(use_sentry=use_sentry),  # type: ignore
        wrapper_class=make_measuring_bound_logger(settings.structlog_level),
        context_class=dict,
        logger_factory=structlog.WriteLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_module_logger() -> FFunBoundLogger:
    caller_frame = inspect.currentframe().f_back  # type: ignore
    module = inspect.getmodule(caller_frame)  # type: ignore
    return structlog.get_logger(module=module.__name__)  # type: ignore


class Constructor:
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def __call__(self, kwargs: dict[str, object]) -> object:
        raise NotImplementedError('You must implement "__call__" in child class')


class IdentityConstructor(Constructor):
    __slots__ = ()

    def __init__(self, arg: str) -> None:
        super().__init__(name=arg)

    def __call__(self, kwargs: dict[str, object]) -> object:
        return kwargs.get(self.name)


class ArgumentConstructor(Constructor):
    __slots__ = ("key", "attribute")

    def __init__(self, arg: str) -> None:
        super().__init__(name=arg.replace(".", "_"))
        self.key, self.attribute = arg.split(".", 1)

    def __call__(self, kwargs: dict[str, object]) -> object:
        if self.key not in kwargs:
            return None

        return getattr(kwargs[self.key], self.attribute, None)  # type: ignore


P = ParamSpec("P")
R = TypeVar("R")


def sync_args_to_log(*args: str) -> Callable[[Callable[P, R]], Callable[P, R]]:
    constructors: list[Constructor] = []

    for arg in args:
        if "." not in arg:
            constructors.append(IdentityConstructor(arg))
        else:
            constructors.append(ArgumentConstructor(arg))

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            assert not args

            with structlog_contextvars.bound_contextvars(**{c.name: c(kwargs) for c in constructors}):
                return func(*args, **kwargs)

        return wrapped

    return decorator


def async_args_to_log(*args: str) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    constructors: list[Constructor] = []

    for arg in args:
        if "." not in arg:
            constructors.append(IdentityConstructor(arg))
        else:
            constructors.append(ArgumentConstructor(arg))

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @functools.wraps(func)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            assert not args

            with structlog_contextvars.bound_contextvars(**{c.name: c(kwargs) for c in constructors}):
                return await func(*args, **kwargs)

        return cast(Callable[P, Awaitable[R]], wrapped)

    return decorator


@contextlib.contextmanager
def bound_log_args(**kwargs: object) -> Iterator[None]:

    if not kwargs:
        yield
        return

    if set(kwargs) & {"m_labels", "m_value", "m_kind", "b_kind"}:
        raise errors.ReservedLogArguments()

    bound_vars: dict[str, object] = structlog_contextvars.get_contextvars()

    if bound_vars.keys() & kwargs.keys():
        raise errors.DuplicatedLogArguments()

    with structlog_contextvars.bound_contextvars(**kwargs):
        yield


@contextlib.contextmanager
def bound_measure_labels(**labels: LabelValue) -> Iterator[None]:
    if not labels:
        yield
        return

    bound_vars: dict[str, object] = structlog_contextvars.get_contextvars()

    if "m_labels" in bound_vars:
        assert isinstance(bound_vars["m_labels"], dict)

        if labels.keys() & bound_vars["m_labels"].keys():
            raise errors.DuplicatedMeasureLabels()

        new_labels = copy.copy(bound_vars["m_labels"])

    else:
        new_labels = {}

    new_labels.update(labels)

    with structlog_contextvars.bound_contextvars(m_labels=new_labels):
        yield
