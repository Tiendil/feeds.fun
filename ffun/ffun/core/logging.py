import datetime
import enum
import inspect
import logging
import os
import uuid
from typing import Any, Iterable

import pydantic
import structlog


class Renderer(str, enum.Enum):
    console = "console"
    json = "json"


class Settings(pydantic.BaseSettings):  # type: ignore
    log_evel: str = "INFO"
    renderer: Renderer = Renderer.console

    class Config:
        env_nested_delimiter: str = "__"
        env_file: str = ".env"
        env_prefix = "FFUN_"
        extra: str = "allow"

    @property
    def structlog_level(self) -> int:
        return getattr(logging, self.log_evel.upper())


settings = Settings()


class Formatter:
    __slots__ = ()

    def can_format(self, value: Any) -> bool:
        raise NotImplementedError()

    def format(self, value: Any) -> Any:
        raise NotImplementedError()


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

    def __call__(self, _, __, event_dict: dict[str, Any]) -> dict[str, Any]:
        for key, value in event_dict.items():
            for formatter in self._formatters:
                if formatter.can_format(value):
                    event_dict[key] = formatter.format(value)
                    break

        return event_dict


def info_extracter(_, __, event_dict: dict[str, Any]) -> dict[str, Any]:
    replaced = False

    for key, value in list(event_dict.items()):
        if not hasattr(value, "log_info"):
            continue

        for k, v in value.log_info().items():
            event_dict[f'{key}_{k}'] = v

        del event_dict[key]

        replaced = True

    if not replaced:
        return event_dict

    return info_extracter(_, __, event_dict)


def create_formatter():
    formatters = [DateFormatter(),
                  UUIDFormatter(),
                  EnumFormatter()]
    return ProcessorFormatter(formatters)


def processors_list():

    processors_list = [
        info_extracter,
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="ISO", utc=True, key="timestamp"),
        create_formatter(),
        structlog.dev.ConsoleRenderer() if settings.renderer == Renderer.console else None,
        structlog.processors.JSONRenderer() if settings.renderer == Renderer.json else None,
    ]

    return [p for p in processors_list if p is not None]


def initialize() -> None:
    structlog.configure(
        processors=processors_list(),
        wrapper_class=structlog.make_filtering_bound_logger(settings.structlog_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True)


def get_module_logger():
    caller_frame = inspect.currentframe().f_back
    module = inspect.getmodule(caller_frame)
    return structlog.get_logger(module=module.__name__)
