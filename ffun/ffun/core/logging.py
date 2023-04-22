import logging

import pydantic
import structlog


class Settings(pydantic.BaseSettings):  # type: ignore
    log_evel: str = "INFO"

    class Config:
        env_nested_delimiter: str = "__"
        env_file: str = ".env"
        env_prefix = "FFUN_"
        extra: str = "allow"

    @property
    def structlog_level(self) -> int:
        return getattr(logging, self.log_evel.upper())


settings = Settings()


def processors_list():

    processors_list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        # structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(),
        structlog.processors.UnicodeDecoder(),
        structlog.dev.ConsoleRenderer()
    ]

    return [p for p in processors_list if p is not None]


def initialize() -> None:
    structlog.configure(
        processors=processors_list(),
        wrapper_class=structlog.make_filtering_bound_logger(settings.structlog_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False)
