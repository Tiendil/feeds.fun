
import sentry_sdk
from sentry_sdk import init as initialize_sentry
from sentry_sdk.integrations.logging import LoggingIntegration


def improve_fingerprint(event, hint):
    if "exc_info" not in hint:
        return event

    _, e, _ = hint["exc_info"]

    if isinstance(e, error.BaseError) and e.fingerprint is not None:
        event["fingerprint"] = ["{{ default }}", e.fingerprint]

    return event


def before_send(event, hint):
    event = improve_fingerprint(event, hint)
    return event


def initialize(dsn: str,
               sample_rate: float,
               traces_sample_rate: float,
               environment: str) -> None:
    initialize_sentry(
        dsn=dsn,
        sample_rate=sample_rate,
        traces_sample_rate=traces_sample_rate,
        attach_stacktrace=True,
        request_bodies="never",
        before_send=before_send,
        environment=environment,
        integrations=[
            # disable default logging integration to use specialized structlog-sentry processor
            LoggingIntegration(event_level=None, level=None),
        ],
    )
