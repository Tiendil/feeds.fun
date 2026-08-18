import asyncio
import json
import uuid
from collections.abc import Coroutine

import typer

from ffun.application.application import with_app
from ffun.core import errors as core_errors
from ffun.core.entities import BaseEntity
from ffun.domain.entities import UserId
from ffun.entitlements import domain as e_domain
from ffun.entitlements.entities import EffectiveEntitlementInterval, EntitlementKindId

cli_app = typer.Typer()


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
