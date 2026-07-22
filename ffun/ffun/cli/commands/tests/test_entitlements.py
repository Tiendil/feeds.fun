import asyncio
import contextlib
import datetime
import json
from typing import cast

import pytest
import typer
from pytest_mock import MockerFixture

from ffun.audit.entities import AuditEntityKind
from ffun.cli.commands import entitlements
from ffun.core import errors as core_errors
from ffun.domain.domain import new_user_id
from ffun.domain.entities import SerializedId, UserId
from ffun.entitlements.entities import (
    LIFETIME_ENTITLEMENT_EXPIRES_AT,
    EffectiveEntitlementInterval,
    EntitlementKindId,
    EntitlementSourceId,
    EntitlementTransactionId,
    SourceEntitlement,
)
from ffun.entitlements.tests.make import make_effective_entitlement_interval


class TestEntitlementKindFromName:
    @pytest.mark.parametrize("kind", list(EntitlementKindId))
    def test_registered_name(self, kind: EntitlementKindId) -> None:
        assert entitlements.entitlement_kind_from_name(kind.name) == kind

    def test_rejects_numeric_value(self) -> None:
        with pytest.raises(typer.BadParameter):
            entitlements.entitlement_kind_from_name(str(EntitlementKindId.day_tokens.value))

    def test_rejects_unknown_name(self) -> None:
        with pytest.raises(typer.BadParameter):
            entitlements.entitlement_kind_from_name("unknown")


class TestActorKindFromName:
    @pytest.mark.parametrize("kind", list(AuditEntityKind))
    def test_registered_name(self, kind: AuditEntityKind) -> None:
        assert entitlements.actor_kind_from_name(kind.name) == kind

    def test_rejects_unknown_name(self) -> None:
        with pytest.raises(typer.BadParameter):
            entitlements.actor_kind_from_name("unknown")


class TestTimestampFromString:
    def test_missing_value(self) -> None:
        assert entitlements.timestamp_from_string(None, option_name="--starts-at") is None

    def test_iso_8601_with_utc_offset(self) -> None:
        timestamp = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=2)))

        assert entitlements.timestamp_from_string(timestamp.isoformat(), option_name="--starts-at") == timestamp

    def test_rejects_invalid_value(self) -> None:
        with pytest.raises(typer.BadParameter):
            entitlements.timestamp_from_string("not-a-timestamp", option_name="--starts-at")

    def test_rejects_value_without_utc_offset(self) -> None:
        timestamp = datetime.datetime.now()

        with pytest.raises(typer.BadParameter):
            entitlements.timestamp_from_string(timestamp.isoformat(), option_name="--starts-at")


class TestResolveTimestamps:
    def test_recurring_defaults_from_one_captured_timestamp(self) -> None:
        captured_at = datetime.datetime.now(tz=datetime.UTC)

        starts_at, expires_at = entitlements.resolve_timestamps(
            EntitlementKindId.day_tokens,
            None,
            None,
            captured_at,
        )

        assert starts_at == captured_at
        assert expires_at == captured_at + datetime.timedelta(days=31)

    def test_lifetime_defaults_to_stable_expiration(self) -> None:
        captured_at = datetime.datetime.now(tz=datetime.UTC)

        starts_at, expires_at = entitlements.resolve_timestamps(
            EntitlementKindId.lifetime_tokens,
            None,
            None,
            captured_at,
        )

        assert starts_at == captured_at
        assert expires_at == LIFETIME_ENTITLEMENT_EXPIRES_AT

    def test_missing_starts_at_defaults_to_captured_timestamp(self) -> None:
        captured_at = datetime.datetime.now(tz=datetime.UTC)
        expires_at = captured_at + datetime.timedelta(days=7)

        assert entitlements.resolve_timestamps(
            EntitlementKindId.day_tokens,
            None,
            expires_at,
            captured_at,
        ) == (captured_at, expires_at)

    def test_missing_expires_at_defaults_from_captured_timestamp(self) -> None:
        captured_at = datetime.datetime.now(tz=datetime.UTC)
        starts_at = captured_at - datetime.timedelta(days=1)

        assert entitlements.resolve_timestamps(
            EntitlementKindId.day_tokens,
            starts_at,
            None,
            captured_at,
        ) == (starts_at, captured_at + datetime.timedelta(days=31))

    def test_preserves_explicit_values(self) -> None:
        starts_at = datetime.datetime.now(tz=datetime.UTC)
        expires_at = starts_at + datetime.timedelta(days=7)

        assert entitlements.resolve_timestamps(
            EntitlementKindId.day_tokens,
            starts_at,
            expires_at,
            starts_at,
        ) == (starts_at, expires_at)


class TestRunGrant:
    @pytest.mark.asyncio
    async def test_passes_command_to_domain(self, mocker: MockerFixture) -> None:
        mocker.patch.object(entitlements, "with_app", return_value=contextlib.nullcontext())
        received: list[tuple[SourceEntitlement, AuditEntityKind, SerializedId]] = []

        async def grant_source_entitlement(
            source_entitlement: SourceEntitlement,
            *,
            actor_kind: AuditEntityKind,
            actor_id: SerializedId,
        ) -> tuple[bool, int | None]:
            received.append((source_entitlement, actor_kind, actor_id))
            return (True, 10)

        mocker.patch.object(entitlements.e_domain, "grant_source_entitlement", side_effect=grant_source_entitlement)
        starts_at = datetime.datetime.now(tz=datetime.UTC)
        source_entitlement = SourceEntitlement(
            source=EntitlementSourceId("test"),
            transaction_id=EntitlementTransactionId("transaction"),
            user_id=new_user_id(),
            kind_id=EntitlementKindId.day_tokens,
            value=10,
            starts_at=starts_at,
            expires_at=starts_at + datetime.timedelta(days=1),
        )
        command = entitlements.GrantCommand(
            source_entitlement=source_entitlement,
            actor_kind=AuditEntityKind.admin,
            actor_id=SerializedId("test-admin"),
        )

        await entitlements.run_grant(command)

        assert received == [
            (
                source_entitlement,
                command.actor_kind,
                command.actor_id,
            )
        ]


class TestRunRevoke:
    @pytest.mark.asyncio
    async def test_passes_identity_to_domain(self, mocker: MockerFixture) -> None:
        mocker.patch.object(entitlements, "with_app", return_value=contextlib.nullcontext())
        received: list[dict[str, object]] = []

        async def revoke_source_entitlement(**kwargs: object) -> tuple[bool, int | None]:
            received.append(kwargs)
            return (False, None)

        mocker.patch.object(entitlements.e_domain, "revoke_source_entitlement", side_effect=revoke_source_entitlement)
        command = entitlements.RevokeCommand(
            source=EntitlementSourceId("test"),
            transaction_id=EntitlementTransactionId("transaction"),
            user_id=new_user_id(),
            kind_id=EntitlementKindId.day_tokens,
            actor_kind=AuditEntityKind.admin,
            actor_id=SerializedId("test-admin"),
        )

        await entitlements.run_revoke(command)

        assert received == [cast(dict[str, object], command.model_dump())]


class TestGrantSourceEntitlement:
    @pytest.mark.asyncio
    async def test_builds_and_runs_command(self, mocker: MockerFixture) -> None:
        received_commands: list[entitlements.GrantCommand] = []

        async def run_grant(command: entitlements.GrantCommand) -> None:
            received_commands.append(command)

        mocker.patch.object(entitlements, "run_grant", side_effect=run_grant)
        user_id = new_user_id()
        started_at = datetime.datetime.now(tz=datetime.UTC)

        await asyncio.to_thread(
            entitlements.grant_source_entitlement,
            user_id=user_id,
            kind="day_tokens",
            source="test",
            transaction_id="transaction",
            value=10,
            starts_at=None,
            expires_at=None,
            actor_kind="admin",
            actor_id="test-admin",
        )

        finished_at = datetime.datetime.now(tz=datetime.UTC)
        assert len(received_commands) == 1
        command = received_commands[0]
        assert started_at <= command.source_entitlement.starts_at <= finished_at
        assert command.source_entitlement.expires_at == command.source_entitlement.starts_at + datetime.timedelta(
            days=31
        )
        assert command.source_entitlement.transaction_id == "transaction"

    @pytest.mark.parametrize("field", ["source", "transaction_id", "actor_id"])
    def test_rejects_invalid_parameter(self, field: str) -> None:
        values: dict[str, object] = {
            "user_id": new_user_id(),
            "kind": "day_tokens",
            "source": "test",
            "transaction_id": "transaction",
            "value": 10,
            "starts_at": None,
            "expires_at": None,
            "actor_kind": "admin",
            "actor_id": "test-admin",
        }
        values[field] = " "

        with pytest.raises(typer.BadParameter, match="invalid grant parameters"):
            entitlements.grant_source_entitlement(**values)  # type: ignore[arg-type]


class TestRevoke:
    @pytest.mark.parametrize("field", ["source", "transaction_id", "actor_id"])
    def test_rejects_invalid_parameter(self, field: str) -> None:
        values: dict[str, object] = {
            "user_id": new_user_id(),
            "kind": "day_tokens",
            "source": "test",
            "transaction_id": "transaction",
            "actor_kind": "admin",
            "actor_id": "test-admin",
        }
        values[field] = " "

        with pytest.raises(typer.BadParameter, match="invalid revoke parameters"):
            entitlements.revoke(**values)  # type: ignore[arg-type]


class TestRunAsyncCommand:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        called = False

        async def command() -> None:
            nonlocal called
            called = True

        await asyncio.to_thread(entitlements.run_async_command, command())

        assert called

    @pytest.mark.asyncio
    async def test_project_error_exits_nonzero(self, capsys: pytest.CaptureFixture[str]) -> None:
        async def command() -> None:
            raise core_errors.CoreError(reason="invalid command")

        with pytest.raises(typer.Exit) as raised:
            await asyncio.to_thread(entitlements.run_async_command, command())

        assert raised.value.exit_code == 1
        assert "CoreError" in capsys.readouterr().err

    @pytest.mark.asyncio
    async def test_unexpected_error_propagates(self) -> None:
        async def command() -> None:
            raise RuntimeError("unexpected command failure")

        with pytest.raises(RuntimeError, match="unexpected command failure"):
            await asyncio.to_thread(entitlements.run_async_command, command())


class TestEntitlementRecord:
    def test_granted(self) -> None:
        user_id = new_user_id()
        interval = make_effective_entitlement_interval(user_id=user_id)

        assert entitlements.entitlement_record(user_id, EntitlementKindId.day_tokens, interval) == {
            "user_id": str(user_id),
            "kind": "day_tokens",
            "kind_id": 1,
            "granted": True,
            "value": interval.value,
            "starts_at": interval.starts_at.isoformat(),
            "expires_at": interval.expires_at.isoformat(),
        }

    def test_not_granted(self) -> None:
        user_id = new_user_id()

        assert entitlements.entitlement_record(user_id, EntitlementKindId.lifetime_tokens, None) == {
            "user_id": str(user_id),
            "kind": "lifetime_tokens",
            "kind_id": 3,
            "granted": False,
            "value": None,
            "starts_at": None,
            "expires_at": None,
        }


class TestRunList:
    @pytest.mark.asyncio
    async def test_outputs_domain_result_as_json(
        self,
        mocker: MockerFixture,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mocker.patch.object(entitlements, "with_app", return_value=contextlib.nullcontext())
        user_id = new_user_id()
        interval = make_effective_entitlement_interval(user_id=user_id)

        async def get_entitlements(
            user_ids: list[UserId],
            kind_ids: list[EntitlementKindId],
        ) -> dict[UserId, dict[EntitlementKindId, EffectiveEntitlementInterval | None]]:
            assert user_ids == [user_id]
            assert kind_ids == [EntitlementKindId.day_tokens, EntitlementKindId.lifetime_tokens]
            return {
                user_id: {
                    EntitlementKindId.day_tokens: interval,
                    EntitlementKindId.lifetime_tokens: None,
                }
            }

        mocker.patch.object(entitlements.e_domain, "get_entitlements", side_effect=get_entitlements)
        await entitlements.run_list(
            entitlements.ListEntitlementsCommand(
                user_ids=[user_id],
                kind_ids=[EntitlementKindId.day_tokens, EntitlementKindId.lifetime_tokens],
            )
        )

        assert capsys.readouterr().out.splitlines() == [
            json.dumps(entitlements.entitlement_record(user_id, EntitlementKindId.day_tokens, interval)),
            json.dumps(entitlements.entitlement_record(user_id, EntitlementKindId.lifetime_tokens, None)),
        ]
