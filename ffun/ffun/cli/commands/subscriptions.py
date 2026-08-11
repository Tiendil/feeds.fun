import asyncio
import datetime
import json
import uuid
from collections.abc import Coroutine

import pydantic
import typer
from tabulate import tabulate

from ffun.application.application import with_app
from ffun.audit.entities import AuditEntityKind
from ffun.core import errors as core_errors
from ffun.core import utils
from ffun.core.entities import BaseEntity
from ffun.domain.entities import SerializedId, UserId
from ffun.subscriptions import domain as s_domain
from ffun.subscriptions import errors as s_errors
from ffun.subscriptions.entities import (
    ProviderId,
    ProviderMerchantId,
    ProviderStatus,
    ProviderSubscriptionId,
    SaveSubscriptionOutcome,
    Subscription,
    SubscriptionStatusId,
)

cli_app = typer.Typer()

DEFAULT_PROVIDER_ID = "feeds-fun-cli"
DEFAULT_PROVIDER_MERCHANT_ID = "feeds-fun"
DEFAULT_SUBSCRIPTION_DURATION = datetime.timedelta(days=31)


class SetSubscriptionCommand(BaseEntity):
    subscription: Subscription
    actor_kind: AuditEntityKind
    actor_id: SerializedId
    json_output: bool = False


class UpdateSubscriptionCommand(BaseEntity):
    user_id: UserId
    provider_id: ProviderId
    provider_merchant_id: ProviderMerchantId
    provider_subscription_id: ProviderSubscriptionId
    status: SubscriptionStatusId | None = None
    provider_status: ProviderStatus | None = None
    started_at: datetime.datetime | None = None
    renews_at: datetime.datetime | None = None
    clear_renews_at: bool = False
    ends_at: datetime.datetime | None = None
    clear_ends_at: bool = False
    provider_updated_at: datetime.datetime
    actor_kind: AuditEntityKind
    actor_id: SerializedId
    json_output: bool = False

    @pydantic.model_validator(mode="after")
    def validate_changes(self) -> "UpdateSubscriptionCommand":
        if self.renews_at is not None and self.clear_renews_at:
            raise ValueError("renews_at and clear_renews_at are mutually exclusive")

        if self.ends_at is not None and self.clear_ends_at:
            raise ValueError("ends_at and clear_ends_at are mutually exclusive")

        if not any(
            (
                self.status is not None,
                self.provider_status is not None,
                self.started_at is not None,
                self.renews_at is not None,
                self.clear_renews_at,
                self.ends_at is not None,
                self.clear_ends_at,
            )
        ):
            raise ValueError("at least one subscription field must be updated")

        return self


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


def actor_kind_from_name(raw_kind: str) -> AuditEntityKind:
    try:
        return AuditEntityKind[raw_kind]
    except KeyError as error:
        valid_names = ", ".join(kind.name for kind in AuditEntityKind)
        raise typer.BadParameter(f"unknown actor kind {raw_kind!r}; expected one of: {valid_names}") from error


def timestamp_from_string(raw_timestamp: str | None, *, option_name: str) -> datetime.datetime | None:
    if raw_timestamp is None:
        return None

    try:
        timestamp = datetime.datetime.fromisoformat(raw_timestamp)
    except ValueError as error:
        raise typer.BadParameter("expected an ISO 8601 timestamp", param_hint=option_name) from error

    if not utils.has_timezone(timestamp):
        raise typer.BadParameter("timestamp must include an explicit UTC offset", param_hint=option_name)

    return timestamp


def subscription_record(subscription: Subscription) -> dict[str, object]:
    return {
        "provider_id": subscription.provider_id,
        "provider_merchant_id": subscription.provider_merchant_id,
        "provider_subscription_id": subscription.provider_subscription_id,
        "user_id": str(subscription.user_id),
        "provider_customer_id": subscription.provider_customer_id,
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
            subscription.provider_id,
            subscription.provider_merchant_id,
            subscription.provider_subscription_id,
            subscription.provider_customer_id,
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
            "provider",
            "merchant",
            "subscription",
            "customer",
            "status",
            "provider status",
            "started",
            "renews",
            "ends",
            "provider updated",
        ],
        tablefmt="grid",
    )


def subscription_change_output(
    outcome: SaveSubscriptionOutcome,
    subscription: Subscription,
    *,
    json_output: bool,
) -> str:
    if json_output:
        output: dict[str, object] = {
            "outcome": outcome.name,
            "outcome_id": outcome.value,
            "subscription": subscription_record(subscription),
        }
        return json.dumps(output)

    return f"{outcome.name.capitalize()} subscription snapshot\n{subscriptions_table([subscription])}"


async def run_set(command: SetSubscriptionCommand) -> None:
    async with with_app():
        outcome: SaveSubscriptionOutcome = await s_domain.save_subscription(
            command.subscription,
            actor_kind=command.actor_kind,
            actor_id=command.actor_id,
        )

    typer.echo(subscription_change_output(outcome, command.subscription, json_output=command.json_output))


def updated_subscription(subscription: Subscription, command: UpdateSubscriptionCommand) -> Subscription:
    changes: dict[str, object] = {"provider_updated_at": command.provider_updated_at}

    if command.status is not None:
        changes["status"] = command.status

    if command.provider_status is not None:
        changes["provider_status"] = command.provider_status

    if command.started_at is not None:
        changes["started_at"] = command.started_at

    if command.renews_at is not None:
        changes["renews_at"] = command.renews_at
    elif command.clear_renews_at:
        changes["renews_at"] = None

    if command.ends_at is not None:
        changes["ends_at"] = command.ends_at
    elif command.clear_ends_at:
        changes["ends_at"] = None

    return subscription.replace(**changes)


async def run_update(command: UpdateSubscriptionCommand) -> None:
    async with with_app():
        subscription = await s_domain.get_subscription(
            provider_id=command.provider_id,
            provider_merchant_id=command.provider_merchant_id,
            provider_subscription_id=command.provider_subscription_id,
        )

        if subscription is None or subscription.user_id != command.user_id:
            raise typer.BadParameter("subscription was not found for the specified user", param_hint="--user-id")

        result_subscription = updated_subscription(subscription, command)
        outcome: SaveSubscriptionOutcome = await s_domain.save_subscription(
            result_subscription,
            actor_kind=command.actor_kind,
            actor_id=command.actor_id,
        )

    typer.echo(subscription_change_output(outcome, result_subscription, json_output=command.json_output))


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


@cli_app.command("set")  # type: ignore
def set_subscription(  # noqa: CCR001, CFQ002
    user_id: uuid.UUID = typer.Option(..., "--user-id"),
    provider_id: str = typer.Option(DEFAULT_PROVIDER_ID, "--provider-id"),
    provider_merchant_id: str | None = typer.Option(None, "--provider-merchant-id"),
    provider_subscription_id: str | None = typer.Option(None, "--provider-subscription-id"),
    provider_customer_id: str | None = typer.Option(None, "--provider-customer-id"),
    status: str = typer.Option("active", "--status"),
    provider_status: str | None = typer.Option(None, "--provider-status"),
    started_at: str | None = typer.Option(None, "--started-at"),
    renews_at: str | None = typer.Option(None, "--renews-at"),
    ends_at: str | None = typer.Option(None, "--ends-at"),
    provider_updated_at: str | None = typer.Option(None, "--provider-updated-at"),
    json_output: bool = typer.Option(False, "--json"),
    actor_kind: str = typer.Option("admin", "--actor-kind"),
    actor_id: str = typer.Option("admin", "--actor-id"),
) -> None:
    captured_at = datetime.datetime.now(tz=datetime.UTC)
    resolved_status = subscription_status_from_name(status)
    resolved_started_at = timestamp_from_string(started_at, option_name="--started-at") or captured_at
    resolved_ends_at = timestamp_from_string(ends_at, option_name="--ends-at")

    missing_provider_identity_options = [
        option_name
        for option_name, option_value in (
            ("--provider-merchant-id", provider_merchant_id),
            ("--provider-subscription-id", provider_subscription_id),
            ("--provider-customer-id", provider_customer_id),
        )
        if option_value is None
    ]
    if provider_id.strip() != DEFAULT_PROVIDER_ID and missing_provider_identity_options:
        missing_options = ", ".join(missing_provider_identity_options)
        raise typer.BadParameter(
            f"non-default --provider-id requires explicit provider identity options: {missing_options}"
        )

    subscription_data: dict[str, object] = {
        "provider_id": provider_id,
        "provider_merchant_id": (
            provider_merchant_id if provider_merchant_id is not None else DEFAULT_PROVIDER_MERCHANT_ID
        ),
        "provider_subscription_id": (
            provider_subscription_id if provider_subscription_id is not None else f"feeds-fun-subscription-{user_id}"
        ),
        "user_id": user_id,
        "provider_customer_id": (
            provider_customer_id if provider_customer_id is not None else f"feeds-fun-user-{user_id}"
        ),
        "status": resolved_status,
        "provider_status": provider_status if provider_status is not None else resolved_status.name,
        "started_at": resolved_started_at,
        "renews_at": timestamp_from_string(renews_at, option_name="--renews-at"),
        "ends_at": (
            resolved_ends_at if resolved_ends_at is not None else resolved_started_at + DEFAULT_SUBSCRIPTION_DURATION
        ),
        "provider_updated_at": (
            timestamp_from_string(provider_updated_at, option_name="--provider-updated-at") or captured_at
        ),
    }

    try:
        command_data: dict[str, object] = {
            "subscription": Subscription.model_validate(subscription_data),
            "actor_kind": actor_kind_from_name(actor_kind),
            "actor_id": actor_id,
            "json_output": json_output,
        }
        command = SetSubscriptionCommand.model_validate(command_data)
    except pydantic.ValidationError as error:
        raise typer.BadParameter("invalid set parameters") from error

    run_async_command(run_set(command))


@cli_app.command("update")  # type: ignore
def update_subscription(  # noqa: CFQ002
    user_id: uuid.UUID = typer.Option(..., "--user-id"),
    provider_id: str = typer.Option(..., "--provider-id"),
    provider_merchant_id: str = typer.Option(..., "--provider-merchant-id"),
    provider_subscription_id: str = typer.Option(..., "--provider-subscription-id"),
    status: str | None = typer.Option(None, "--status"),
    provider_status: str | None = typer.Option(None, "--provider-status"),
    started_at: str | None = typer.Option(None, "--started-at"),
    renews_at: str | None = typer.Option(None, "--renews-at"),
    clear_renews_at: bool = typer.Option(False, "--clear-renews-at"),
    ends_at: str | None = typer.Option(None, "--ends-at"),
    clear_ends_at: bool = typer.Option(False, "--clear-ends-at"),
    provider_updated_at: str | None = typer.Option(None, "--provider-updated-at"),
    json_output: bool = typer.Option(False, "--json"),
    actor_kind: str = typer.Option("admin", "--actor-kind"),
    actor_id: str = typer.Option("admin", "--actor-id"),
) -> None:
    captured_at = datetime.datetime.now(tz=datetime.UTC)

    try:
        command_data: dict[str, object] = {
            "user_id": user_id,
            "provider_id": provider_id,
            "provider_merchant_id": provider_merchant_id,
            "provider_subscription_id": provider_subscription_id,
            "status": subscription_status_from_name(status) if status is not None else None,
            "provider_status": provider_status,
            "started_at": timestamp_from_string(started_at, option_name="--started-at"),
            "renews_at": timestamp_from_string(renews_at, option_name="--renews-at"),
            "clear_renews_at": clear_renews_at,
            "ends_at": timestamp_from_string(ends_at, option_name="--ends-at"),
            "clear_ends_at": clear_ends_at,
            "provider_updated_at": (
                timestamp_from_string(provider_updated_at, option_name="--provider-updated-at") or captured_at
            ),
            "actor_kind": actor_kind_from_name(actor_kind),
            "actor_id": actor_id,
            "json_output": json_output,
        }
        command = UpdateSubscriptionCommand.model_validate(command_data)
    except pydantic.ValidationError as error:
        raise typer.BadParameter("invalid update parameters") from error

    run_async_command(run_update(command))


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
