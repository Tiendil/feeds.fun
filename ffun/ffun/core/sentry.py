from typing import TYPE_CHECKING, Any

from sentry_sdk import init as initialize_sentry

if TYPE_CHECKING:
    from sentry_sdk._types import Event

from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from ffun.core.errors import Error


def improve_fingerprint(event: "Event", hint: dict[str, Any]) -> "Event":
    if "exc_info" not in hint:
        return event

    _, e, _ = hint["exc_info"]

    if isinstance(e, Error) and e.fingerprint is not None:
        event["fingerprint"] = ["{{ default }}", e.fingerprint]

    return event


def before_send(event: "Event", hint: dict[str, Any]) -> "Event":
    return improve_fingerprint(event, hint)


def initialize(dsn: str, sample_rate: float, traces_sample_rate: float, environment: str) -> None:
    initialize_sentry(
        dsn=dsn,
        sample_rate=sample_rate,
        traces_sample_rate=traces_sample_rate,
        attach_stacktrace=True,
        before_send=before_send,
        environment=environment,
        include_source_context=True,
        integrations=[
            # disable default logging integration to use specialized structlog-sentry processor
            LoggingIntegration(event_level=None, level=None),
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
    )
