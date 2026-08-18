import asyncio
import json
import uuid
from collections.abc import Coroutine

import pydantic
import typer
from tabulate import tabulate

from ffun.application.application import with_app
from ffun.core import errors as core_errors
from ffun.core.entities import BaseEntity
from ffun.domain.entities import UserId
from ffun.subscriptions import domain as s_domain
from ffun.subscriptions import errors as s_errors
from ffun.subscriptions.entities import Subscription, SubscriptionStatusId

cli_app = typer.Typer()


class ListSubscriptionsCommand(BaseEntity):
    user_id: UserId
    statuses: list[SubscriptionStatusId] | None = None
    alive_only: bool = False
    json_output: bool = False

    @pydantic.model_validator(mode="after")
    def validate_filters(self) -> "ListSubscriptionsCommand":
        if self.alive_only and self.statuses is not None:
            raise ValueError("alive and status filters are mutually exclusive")

        return self


def run_async_command(command: Coroutine[object, object, None]) -> None:
    try:
        asyncio.run(command)
    except s_errors.InvalidStoredSubscription:
        raise
    except core_errors.Error as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def subscription_status_from_name(raw_status: str) -> SubscriptionStatusId:
    try:
        return SubscriptionStatusId[raw_status]
    except KeyError as error:
        valid_names = ", ".join(status.name for status in SubscriptionStatusId)
        raise typer.BadParameter(
            f"unknown subscription status {raw_status!r}; expected one of: {valid_names}"
        ) from error


def subscription_record(subscription: Subscription) -> dict[str, object]:
    return {
        "id": str(subscription.id),
        "state_transaction_id": str(subscription.state_transaction_id),
        "user_id": str(subscription.user_id),
        "benefit_id": subscription.benefit_id,
        "status": subscription.status.name,
        "status_id": subscription.status.value,
        "provider_status": subscription.provider_status,
        "started_at": subscription.started_at.isoformat(),
        "renews_at": subscription.renews_at.isoformat() if subscription.renews_at is not None else None,
        "ends_at": subscription.ends_at.isoformat() if subscription.ends_at is not None else None,
        "provider_updated_at": subscription.provider_updated_at.isoformat(),
    }


def subscriptions_table(subscriptions: list[Subscription]) -> str:
    rows = [
        [
            subscription.id,
            subscription.benefit_id,
            subscription.status.name,
            subscription.provider_status,
            subscription.started_at.isoformat(),
            subscription.renews_at.isoformat() if subscription.renews_at is not None else "-",
            subscription.ends_at.isoformat() if subscription.ends_at is not None else "-",
            subscription.provider_updated_at.isoformat(),
        ]
        for subscription in subscriptions
    ]
    return tabulate(
        rows,
        headers=[
            "subscription",
            "benefit",
            "status",
            "provider status",
            "started",
            "renews",
            "ends",
            "provider updated",
        ],
        tablefmt="grid",
    )


async def run_list(command: ListSubscriptionsCommand) -> None:
    async with with_app():
        if command.alive_only:
            subscriptions = await s_domain.get_alive_subscriptions_for_user(command.user_id)
        else:
            subscriptions = await s_domain.get_subscriptions_for_user(command.user_id, statuses=command.statuses)

    if command.json_output:
        for subscription in subscriptions:
            typer.echo(json.dumps(subscription_record(subscription)))
        return

    typer.echo(subscriptions_table(subscriptions))


@cli_app.command("list")  # type: ignore
def list_subscriptions(
    user_id: uuid.UUID = typer.Option(..., "--user-id"),
    statuses: list[str] | None = typer.Option(None, "--status"),
    alive: bool = typer.Option(False, "--alive"),
    json_output: bool = typer.Option(False, "--json"),
) -> None:
    try:
        command = ListSubscriptionsCommand(
            user_id=UserId(user_id),
            statuses=[subscription_status_from_name(status) for status in statuses] if statuses else None,
            alive_only=alive,
            json_output=json_output,
        )
    except pydantic.ValidationError as error:
        raise typer.BadParameter("invalid list parameters") from error

    run_async_command(run_list(command))
