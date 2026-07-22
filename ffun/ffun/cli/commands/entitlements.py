import asyncio
import datetime
import json
import uuid
from collections.abc import Coroutine

import pydantic
import typer

from ffun.application.application import with_app
from ffun.audit.entities import AuditEntityKind
from ffun.core import errors as core_errors
from ffun.core import utils
from ffun.core.entities import BaseEntity
from ffun.domain.entities import SerializedId, UserId
from ffun.entitlements import domain as e_domain
from ffun.entitlements.entities import (
    LIFETIME_ENTITLEMENT_EXPIRES_AT,
    EffectiveEntitlementInterval,
    EntitlementKindId,
    EntitlementSourceId,
    EntitlementTransactionId,
    SourceEntitlement,
)

cli_app = typer.Typer()


class GrantCommand(BaseEntity):
    source_entitlement: SourceEntitlement
    actor_kind: AuditEntityKind
    actor_id: SerializedId


class RevokeCommand(BaseEntity):
    source: EntitlementSourceId
    transaction_id: EntitlementTransactionId
    user_id: UserId
    kind_id: EntitlementKindId
    actor_kind: AuditEntityKind
    actor_id: SerializedId


class ListEntitlementsCommand(BaseEntity):
    user_ids: list[UserId]
    kind_ids: list[EntitlementKindId]


def run_async_command(command: Coroutine[object, object, None]) -> None:
    try:
        asyncio.run(command)
    except core_errors.Error as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def entitlement_kind_from_name(raw_kind: str) -> EntitlementKindId:
    try:
        return EntitlementKindId[raw_kind]
    except KeyError as error:
        valid_names = ", ".join(kind.name for kind in EntitlementKindId)
        raise typer.BadParameter(f"unknown entitlement kind {raw_kind!r}; expected one of: {valid_names}") from error


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


def resolve_timestamps(
    kind_id: EntitlementKindId,
    starts_at: datetime.datetime | None,
    expires_at: datetime.datetime | None,
    captured_at: datetime.datetime,
) -> tuple[datetime.datetime, datetime.datetime]:
    return (
        starts_at if starts_at is not None else captured_at,
        (
            expires_at
            if expires_at is not None
            else (
                LIFETIME_ENTITLEMENT_EXPIRES_AT
                if e_domain.get_entitlement_kind(kind_id).is_lifetime
                else captured_at + datetime.timedelta(days=31)
            )
        ),
    )


async def run_grant(command: GrantCommand) -> None:
    async with with_app():
        await e_domain.grant_source_entitlement(
            command.source_entitlement,
            actor_kind=command.actor_kind,
            actor_id=command.actor_id,
        )


async def run_revoke(command: RevokeCommand) -> None:
    async with with_app():
        await e_domain.revoke_source_entitlement(
            source=command.source,
            transaction_id=command.transaction_id,
            user_id=command.user_id,
            kind_id=command.kind_id,
            actor_kind=command.actor_kind,
            actor_id=command.actor_id,
        )


def grant_source_entitlement(  # noqa: CFQ002
    *,
    user_id: uuid.UUID,
    kind: str,
    source: str,
    transaction_id: str,
    value: int,
    starts_at: str | None,
    expires_at: str | None,
    actor_kind: str,
    actor_id: str,
) -> None:
    captured_at = datetime.datetime.now(tz=datetime.UTC)
    kind_id = entitlement_kind_from_name(kind)
    resolved_starts_at, resolved_expires_at = resolve_timestamps(
        kind_id,
        timestamp_from_string(starts_at, option_name="--starts-at"),
        timestamp_from_string(expires_at, option_name="--expires-at"),
        captured_at,
    )
    source_entitlement_data: dict[str, object] = {
        "source": source,
        "transaction_id": transaction_id,
        "user_id": user_id,
        "kind_id": kind_id,
        "value": value,
        "starts_at": resolved_starts_at,
        "expires_at": resolved_expires_at,
    }
    try:
        command_data: dict[str, object] = {
            "source_entitlement": SourceEntitlement.model_validate(source_entitlement_data),
            "actor_kind": actor_kind_from_name(actor_kind),
            "actor_id": actor_id,
        }
        command = GrantCommand.model_validate(command_data)
    except pydantic.ValidationError as error:
        raise typer.BadParameter("invalid grant parameters") from error

    run_async_command(run_grant(command))


@cli_app.command()  # type: ignore
def grant(  # noqa: CFQ002
    user_id: uuid.UUID = typer.Option(..., "--user-id"),
    kind: str = typer.Option(..., "--kind"),
    source: str = typer.Option("system", "--source"),
    transaction_id: str = typer.Option(..., "--transaction-id"),
    value: int = typer.Option(..., "--value"),
    starts_at: str | None = typer.Option(None, "--starts-at"),
    expires_at: str | None = typer.Option(None, "--expires-at"),
    actor_kind: str = typer.Option("admin", "--actor-kind"),
    actor_id: str = typer.Option("admin", "--actor-id"),
) -> None:
    grant_source_entitlement(
        user_id=user_id,
        kind=kind,
        source=source,
        transaction_id=transaction_id,
        value=value,
        starts_at=starts_at,
        expires_at=expires_at,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )


@cli_app.command()  # type: ignore
def revoke(  # noqa: CFQ002
    user_id: uuid.UUID = typer.Option(..., "--user-id"),
    kind: str = typer.Option(..., "--kind"),
    source: str = typer.Option("system", "--source"),
    transaction_id: str = typer.Option(..., "--transaction-id"),
    actor_kind: str = typer.Option("admin", "--actor-kind"),
    actor_id: str = typer.Option("admin", "--actor-id"),
) -> None:
    try:
        command_data: dict[str, object] = {
            "source": source,
            "transaction_id": transaction_id,
            "user_id": user_id,
            "kind_id": entitlement_kind_from_name(kind),
            "actor_kind": actor_kind_from_name(actor_kind),
            "actor_id": actor_id,
        }
        command = RevokeCommand.model_validate(command_data)
    except pydantic.ValidationError as error:
        raise typer.BadParameter("invalid revoke parameters") from error

    run_async_command(run_revoke(command))


def entitlement_record(
    user_id: UserId,
    kind_id: EntitlementKindId,
    interval: EffectiveEntitlementInterval | None,
) -> dict[str, object]:
    return {
        "user_id": str(user_id),
        "kind": kind_id.name,
        "kind_id": kind_id.value,
        "granted": interval is not None,
        "value": interval.value if interval is not None else None,
        "starts_at": interval.starts_at.isoformat() if interval is not None else None,
        "expires_at": interval.expires_at.isoformat() if interval is not None else None,
    }


async def run_list(command: ListEntitlementsCommand) -> None:
    async with with_app():
        result = await e_domain.get_entitlements(command.user_ids, command.kind_ids)

    for user_id, entitlements in result.items():
        for kind_id, interval in entitlements.items():
            typer.echo(json.dumps(entitlement_record(user_id, kind_id, interval)))


@cli_app.command("list")  # type: ignore
def list_entitlements(
    user_ids: list[uuid.UUID] = typer.Option(..., "--user-id"),
    kinds: list[str] | None = typer.Option(None, "--kind"),
) -> None:
    run_async_command(
        run_list(
            ListEntitlementsCommand(
                user_ids=[UserId(user_id) for user_id in user_ids],
                kind_ids=[entitlement_kind_from_name(kind) for kind in kinds or []],
            )
        )
    )
