import asyncio
import contextlib
import json

import pytest
import typer
from pytest_mock import MockerFixture

from ffun.cli.commands import entitlements
from ffun.core import errors as core_errors
from ffun.domain.domain import new_user_id
from ffun.domain.entities import UserId
from ffun.entitlements.entities import EffectiveEntitlementInterval, EntitlementKindId
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


class TestListEntitlements:
    @pytest.mark.asyncio
    async def test_builds_and_runs_command(self, mocker: MockerFixture) -> None:
        received: list[entitlements.ListEntitlementsCommand] = []

        async def run_list(command: entitlements.ListEntitlementsCommand) -> None:
            received.append(command)

        mocker.patch.object(entitlements, "run_list", side_effect=run_list)
        first_user_id = new_user_id()
        second_user_id = new_user_id()

        await asyncio.to_thread(
            entitlements.list_entitlements,
            user_ids=[first_user_id, second_user_id],
            kinds=["day_tokens", "lifetime_tokens"],
        )

        assert received == [
            entitlements.ListEntitlementsCommand(
                user_ids=[first_user_id, second_user_id],
                kind_ids=[EntitlementKindId.day_tokens, EntitlementKindId.lifetime_tokens],
            )
        ]
