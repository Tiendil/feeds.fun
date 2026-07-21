import asyncio
import contextlib
import datetime
import json

import pytest
import typer
from pytest_mock import MockerFixture

from ffun.audit.entities import AuditEntityKind
from ffun.cli.commands import entitlements
from ffun.core import errors as core_errors
from ffun.domain.domain import new_user_id
from ffun.domain.entities import SerializedId, UserId
from ffun.entitlements.entities import EffectiveEntitlementInterval, EntitlementKindId, EntitlementSourceId
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
        timestamp = datetime.datetime.now().replace(tzinfo=None)

        with pytest.raises(typer.BadParameter):
            entitlements.timestamp_from_string(timestamp.isoformat(), option_name="--starts-at")


class TestResolveTimestamps:
    def test_defaults_from_one_captured_timestamp(self) -> None:
        captured_at = datetime.datetime.now(tz=datetime.UTC)

        starts_at, expires_at = entitlements.resolve_timestamps(None, None, captured_at)

        assert starts_at == captured_at
        assert expires_at == captured_at + datetime.timedelta(days=31)

    def test_preserves_explicit_values(self) -> None:
        starts_at = datetime.datetime.now(tz=datetime.UTC)
        expires_at = starts_at + datetime.timedelta(days=7)

        assert entitlements.resolve_timestamps(starts_at, expires_at, starts_at) == (starts_at, expires_at)

    def test_defaults_only_start(self) -> None:
        captured_at = datetime.datetime.now(tz=datetime.UTC)
        expires_at = captured_at + datetime.timedelta(days=7)

        assert entitlements.resolve_timestamps(None, expires_at, captured_at) == (captured_at, expires_at)

    def test_defaults_only_expiration(self) -> None:
        captured_at = datetime.datetime.now(tz=datetime.UTC)
        starts_at = captured_at - datetime.timedelta(days=1)

        assert entitlements.resolve_timestamps(starts_at, None, captured_at) == (
            starts_at,
            captured_at + datetime.timedelta(days=31),
        )


class TestRunSourceChange:
    @pytest.mark.asyncio
    async def test_passes_command_to_domain(self, mocker: MockerFixture) -> None:
        mocker.patch.object(entitlements, "with_app", return_value=contextlib.nullcontext())
        received_commands: list[entitlements.SourceChangeCommand] = []

        async def change_source_entitlement(  # noqa: CFQ002
            *,
            source: EntitlementSourceId,
            user_id: UserId,
            kind_id: EntitlementKindId,
            granted: bool,
            value: int | None,
            starts_at: datetime.datetime,
            expires_at: datetime.datetime,
            actor_kind: AuditEntityKind,
            actor_id: SerializedId,
        ) -> tuple[bool, int | None]:
            received_commands.append(
                entitlements.SourceChangeCommand(
                    source=source,
                    user_id=user_id,
                    kind_id=kind_id,
                    granted=granted,
                    value=value,
                    starts_at=starts_at,
                    expires_at=expires_at,
                    actor_kind=actor_kind,
                    actor_id=actor_id,
                )
            )
            return (True, value)

        mocker.patch.object(
            entitlements.e_domain,
            "change_source_entitlement",
            side_effect=change_source_entitlement,
        )
        starts_at = datetime.datetime.now(tz=datetime.UTC)
        command = entitlements.SourceChangeCommand(
            source=EntitlementSourceId("test"),
            user_id=new_user_id(),
            kind_id=EntitlementKindId.day_tokens,
            granted=True,
            value=10,
            starts_at=starts_at,
            expires_at=starts_at + datetime.timedelta(days=1),
            actor_kind=AuditEntityKind.admin,
            actor_id=SerializedId("test-admin"),
        )

        await entitlements.run_source_change(command)

        assert received_commands == [command]


class TestChangeSourceEntitlement:
    @pytest.mark.asyncio
    async def test_builds_and_runs_command(self, mocker: MockerFixture) -> None:
        received_commands: list[entitlements.SourceChangeCommand] = []

        async def run_source_change(command: entitlements.SourceChangeCommand) -> None:
            received_commands.append(command)

        mocker.patch.object(entitlements, "run_source_change", side_effect=run_source_change)
        user_id = new_user_id()
        started_at = datetime.datetime.now(tz=datetime.UTC)

        await asyncio.to_thread(
            entitlements.change_source_entitlement,
            user_id=user_id,
            kind="day_tokens",
            source="test",
            granted=True,
            value=10,
            starts_at=None,
            expires_at=None,
            actor_kind="admin",
            actor_id="test-admin",
        )

        finished_at = datetime.datetime.now(tz=datetime.UTC)
        assert len(received_commands) == 1
        command = received_commands[0]
        assert started_at <= command.starts_at <= finished_at
        assert command.expires_at == command.starts_at + datetime.timedelta(days=31)
        assert command == entitlements.SourceChangeCommand(
            source=EntitlementSourceId("test"),
            user_id=user_id,
            kind_id=EntitlementKindId.day_tokens,
            granted=True,
            value=10,
            starts_at=command.starts_at,
            expires_at=command.expires_at,
            actor_kind=AuditEntityKind.admin,
            actor_id=SerializedId("test-admin"),
        )


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
            raise RuntimeError("unexpected failure")

        with pytest.raises(RuntimeError, match="unexpected failure"):
            await asyncio.to_thread(entitlements.run_async_command, command())


class TestEntitlementRecord:
    def test_granted(self) -> None:
        user_id = new_user_id()
        interval = make_effective_entitlement_interval(user_id=user_id, kind_id=EntitlementKindId.day_tokens)

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

        assert entitlements.entitlement_record(user_id, EntitlementKindId.month_tokens, None) == {
            "user_id": str(user_id),
            "kind": "month_tokens",
            "kind_id": 2,
            "granted": False,
            "value": None,
            "starts_at": None,
            "expires_at": None,
        }


class TestRunList:
    @pytest.mark.asyncio
    async def test_outputs_domain_result_as_json(
        self, mocker: MockerFixture, capsys: pytest.CaptureFixture[str]
    ) -> None:
        mocker.patch.object(entitlements, "with_app", return_value=contextlib.nullcontext())
        user_id = new_user_id()
        interval = make_effective_entitlement_interval(
            user_id=user_id,
            kind_id=EntitlementKindId.day_tokens,
        )
        received_user_ids: list[list[UserId]] = []
        received_kind_ids: list[list[EntitlementKindId]] = []

        async def get_entitlements(
            user_ids: list[UserId], kind_ids: list[EntitlementKindId]
        ) -> dict[UserId, dict[EntitlementKindId, EffectiveEntitlementInterval | None]]:  # noqa: TAE002
            received_user_ids.append(user_ids)
            received_kind_ids.append(kind_ids)
            return {
                user_id: {
                    EntitlementKindId.day_tokens: interval,
                    EntitlementKindId.month_tokens: None,
                }
            }

        mocker.patch.object(
            entitlements.e_domain,
            "get_entitlements",
            side_effect=get_entitlements,
        )
        command = entitlements.ListEntitlementsCommand(
            user_ids=[user_id],
            kind_ids=[EntitlementKindId.day_tokens, EntitlementKindId.month_tokens],
        )

        await entitlements.run_list(command)

        assert received_user_ids == [command.user_ids]
        assert received_kind_ids == [command.kind_ids]
        granted_record: dict[str, object] = {
            "user_id": str(user_id),
            "kind": "day_tokens",
            "kind_id": 1,
            "granted": True,
            "value": interval.value,
            "starts_at": interval.starts_at.isoformat(),
            "expires_at": interval.expires_at.isoformat(),
        }
        not_granted_record: dict[str, object] = {
            "user_id": str(user_id),
            "kind": "month_tokens",
            "kind_id": 2,
            "granted": False,
            "value": None,
            "starts_at": None,
            "expires_at": None,
        }
        assert capsys.readouterr().out.splitlines() == [
            json.dumps(granted_record),
            json.dumps(not_granted_record),
        ]
