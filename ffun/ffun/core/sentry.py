from typing import TYPE_CHECKING, Any

from sentry_sdk import init as initialize_sentry

if TYPE_CHECKING:
    from sentry_sdk._types import Event

from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

import ffun
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


def initialize(dsn: str, sample_rate: float, environment: str) -> None:
    initialize_sentry(
        dsn=dsn,
        sample_rate=sample_rate,
        # Background worker traces are not useful
        # because most of the reported ones are related to previous tasks.
        # It can be fixed by reinitializing Sentry's transaction context
        # but it is not worth the effort for now.
        traces_sample_rate=None,
        # Disable breadcrumbs by the same cause — does not work well with background workers.
        max_breadcrumbs=0,
        # Without this config Sentry miss important frames from stacktraces
        add_full_stack=True,
        attach_stacktrace=True,
        before_send=before_send,
        environment=environment,
        # set the correct project root directory
        project_root=ffun.__path__[0],
        # disable ALL automatically enabled integrations, because they periodically cause issues
        # like false positive errors for correctly handled exceptions in OpenAI integration
        auto_enabling_integrations=False,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        disabled_integrations=[
            # disable default logging integration to use specialized structlog-sentry processor
            LoggingIntegration(event_level=None, level=None),
        ],
    )
