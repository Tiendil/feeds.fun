import contextlib
import copy
import datetime
import enum
import functools
import inspect
import logging
import time
import uuid
from collections import abc
from typing import Any, Callable, ContextManager, Iterable, Iterator, Protocol, TypeVar

import pydantic_settings
import structlog
from sentry_sdk import capture_message
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
    async def __call__(self, _: Any, __: Any, event_dict: dict[str, Any]) -> dict[str, Any]:
        pass


class Formatter:
    __slots__ = ()

    def can_format(self, value: Any) -> bool:
        raise NotImplementedError('You must implement "can_format" in child class')

    def format(self, value: Any) -> Any:
        raise NotImplementedError('You must implement "format" in child class')


class DateFormatter(Formatter):
    __slots__ = ()

    def can_format(self, value: Any) -> bool:
        return isinstance(value, (datetime.date, datetime.datetime))

    def format(self, value: Any) -> Any:
        return value.isoformat()


class UUIDFormatter(Formatter):
    __slots__ = ()

    def can_format(self, value: Any) -> bool:
        return isinstance(value, uuid.UUID)

    def format(self, value: Any) -> Any:
        return str(value)


class EnumFormatter(Formatter):
    __slots__ = ()

    def can_format(self, value: Any) -> bool:
        return isinstance(value, enum.Enum)

    def format(self, value: Any) -> Any:
        return value.name


class ProcessorFormatter:
    __slots__ = ("_formatters",)

    def __init__(self, formatters: Iterable[Formatter]) -> None:
        self._formatters = list(formatters)

    def __call__(self, _: Any, __: Any, event_dict: dict[str, Any]) -> dict[str, Any]:
        for key, value in event_dict.items():
            for formatter in self._formatters:
                if formatter.can_format(value):
                    event_dict[key] = formatter.format(value)
                    break

        return event_dict


def info_extracter(_: Any, __: Any, event_dict: dict[str, Any]) -> dict[str, Any]:
    replaced = False

    for key, value in list(event_dict.items()):
        if not hasattr(value, "log_info"):
            continue

        for k, v in value.log_info().items():
            event_dict[f"{key}_{k}"] = v

        del event_dict[key]

        replaced = True

    if not replaced:
        return event_dict

    return info_extracter(_, __, event_dict)


def create_formatter() -> ProcessorFormatter:
    formatters = [DateFormatter(), UUIDFormatter(), EnumFormatter()]
    return ProcessorFormatter(formatters)


def log_errors_to_sentry(_: Any, __: Any, event_dict: dict[str, Any]) -> dict[str, Any]:
    if event_dict.get("sentry_skip"):
        return event_dict

    if event_dict.get("level", "").upper() != "ERROR":
        return event_dict

    capture_message(event_dict["event"])

    return event_dict


def processors_list(use_sentry: bool) -> list[LogProcessorType]:
    sentry_processor = None

    if use_sentry:
        sentry_processor = log_errors_to_sentry

    processors_list = [
        structlog.contextvars.merge_contextvars,
        info_extracter,
        structlog.processors.add_log_level,
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

    def _normalize_value(self, value: Any) -> Any:
        pass

    def business_event(self, event: str, user_id: UserId | None, **attributes: Any) -> Any:
        pass

    def business_slice(self, event: str, user_id: UserId | None, **attributes: LabelValue) -> Any:
        pass


class MeasuringBoundLoggerMixin:
    """We extend a logger class with additional metrics logic.

    This mixin is required to work with metrics in 100% the same way as with logs.

    By calling `logging.measure(...)` and other methods, we guarantee that metrics will have the exact attributes
    as expected from log messages (both custom and general like "module"), so the third-party software
    would be able to filter/process messages universally.
    """

    def measure(self, event: str, value: float | int, **labels: LabelValue) -> Any:
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

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, int | str | float | None):
            return value

        if isinstance(value, abc.Mapping):
            return {str(k): self._normalize_value(v) for k, v in value.items()}

        if isinstance(value, abc.Sequence):
            return [self._normalize_value(v) for v in value]

        return str(value)

    def business_event(self, event: str, user_id: UserId | None, **attributes: LabelValue) -> Any:
        return self.info(  # type: ignore
            event,
            b_kind="event",
            b_user_id=str(user_id) if user_id is not None else None,
            b_uid=str(uuid.uuid4()),
            b_attributes=self._normalize_value(attributes),
        )

    # TODO: test
    def business_slice(self, event: str, user_id: UserId | None, **attributes: LabelValue) -> Any:
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
    module = inspect.getmodule(caller_frame)
    return structlog.get_logger(module=module.__name__)  # type: ignore


FUNC = TypeVar("FUNC", bound=Callable[..., Any])


class Constructor:
    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def __call__(self, kwargs: dict[str, Any]) -> Any:
        raise NotImplementedError('You must implement "__call__" in child class')


class IdentityConstructor(Constructor):
    __slots__ = ()

    def __init__(self, arg: str) -> None:
        super().__init__(name=arg)

    def __call__(self, kwargs: dict[str, Any]) -> Any:
        return kwargs.get(self.name)


class ArgumentConstructor(Constructor):
    __slots__ = ("key", "attribute")

    def __init__(self, arg: str) -> None:
        super().__init__(name=arg.replace(".", "_"))
        self.key, self.attribute = arg.split(".", 1)

    def __call__(self, kwargs: dict[str, Any]) -> Any:
        if self.key not in kwargs:
            return None

        return getattr(kwargs[self.key], self.attribute, None)


def function_args_to_log(*args: str) -> Callable[[FUNC], FUNC]:
    constructors: list[Constructor] = []

    for arg in args:
        if "." not in arg:
            constructors.append(IdentityConstructor(arg))
        else:
            constructors.append(ArgumentConstructor(arg))

    def wrapper(func: FUNC) -> FUNC:
        @functools.wraps(func)
        def wrapped(**kwargs: Any) -> Any:
            with structlog_contextvars.bound_contextvars(**{c.name: c(kwargs) for c in constructors}):
                return func(**kwargs)

        @functools.wraps(func)
        async def async_wrapped(**kwargs: Any) -> Any:
            with structlog_contextvars.bound_contextvars(**{c.name: c(kwargs) for c in constructors}):
                return await func(**kwargs)

        if inspect.iscoroutinefunction(func):
            return async_wrapped  # type: ignore

        return wrapped  # type: ignore

    return wrapper


@contextlib.contextmanager
def bound_log_args(**kwargs: Any) -> Iterator[None]:

    if not kwargs:
        yield
        return

    if kwargs.keys() & {"m_labels", "m_value", "m_kind", "b_kind"}:
        raise errors.ReservedLogArguments()

    bound_vars = structlog_contextvars.get_contextvars()

    if bound_vars.keys() & kwargs.keys():
        raise errors.DuplicatedLogArguments()

    with structlog_contextvars.bound_contextvars(**kwargs):
        yield


@contextlib.contextmanager
def bound_measure_labels(**labels: LabelValue) -> Iterator[None]:
    if not labels:
        yield
        return

    bound_vars = structlog_contextvars.get_contextvars()

    if "m_labels" in bound_vars:
        if labels.keys() & bound_vars["m_labels"].keys():
            raise errors.DuplicatedMeasureLabels()

        new_labels = copy.copy(bound_vars["m_labels"])

    else:
        new_labels = {}

    new_labels.update(labels)

    with structlog_contextvars.bound_contextvars(m_labels=new_labels):
        yield
