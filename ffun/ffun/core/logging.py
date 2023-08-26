import datetime
import enum
import functools
import inspect
import logging
import uuid
from typing import Any, Callable, Iterable, Protocol, TypeVar

import pydantic_settings
import structlog
from sentry_sdk import capture_message
from structlog.contextvars import bound_contextvars


class Renderer(str, enum.Enum):
    console = "console"
    json = "json"


class Settings(pydantic_settings.BaseSettings):
    log_evel: str = "INFO"
    renderer: Renderer = Renderer.console

    model_config = pydantic_settings.SettingsConfigDict(
        env_nested_delimiter="__", env_file=".env", env_prefix="FFUN_", extra="allow"
    )

    @property
    def structlog_level(self) -> int:
        return getattr(logging, self.log_evel.upper())  # type: ignore


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


def initialize(use_sentry: bool) -> None:
    structlog.configure(
        processors=processors_list(use_sentry=use_sentry),  # type: ignore
        wrapper_class=structlog.make_filtering_bound_logger(settings.structlog_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_module_logger() -> structlog.stdlib.BoundLogger:
    caller_frame = inspect.currentframe().f_back  # type: ignore
    module = inspect.getmodule(caller_frame)
    return structlog.get_logger(module=module.__name__)  # type: ignore


FUNC = TypeVar("FUNC", bound=Callable[..., Any])


def bound_function(skip: Iterable[str] = ()) -> Callable[[FUNC], FUNC]:
    def wrapper(func: FUNC) -> FUNC:
        @functools.wraps(func)
        def wrapped(**kwargs: Any) -> Any:
            with bound_contextvars(**{k: v for k, v in kwargs.items() if k not in skip}):
                return func(**kwargs)

        @functools.wraps(func)
        async def async_wrapped(**kwargs: Any) -> Any:
            with bound_contextvars(**{k: v for k, v in kwargs.items() if k not in skip}):
                return await func(**kwargs)

        if inspect.iscoroutinefunction(func):
            return async_wrapped  # type: ignore

        return wrapped  # type: ignore

    return wrapper
