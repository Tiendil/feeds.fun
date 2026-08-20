import asyncio
import contextlib
import datetime
import json

import pydantic
import pytest
import typer
from pytest_mock import MockerFixture

from ffun.cli.commands import subscriptions
from ffun.core import errors as core_errors
from ffun.domain.domain import new_user_id
from ffun.domain.entities import UserId
from ffun.subscriptions import errors as subscription_errors
from ffun.subscriptions.entities import ProviderStatus, Subscription, SubscriptionStatusId
from ffun.subscriptions.tests.make import make_subscription


class TestListSubscriptionsCommand:
    def test_accepts_status_filters(self) -> None:
        command = subscriptions.ListSubscriptionsCommand(
            user_id=new_user_id(),
            statuses=[SubscriptionStatusId.active],
        )

        assert command.statuses == [SubscriptionStatusId.active]

    def test_accepts_alive_only(self) -> None:
        command = subscriptions.ListSubscriptionsCommand(user_id=new_user_id(), alive_only=True)

        assert command.alive_only

    def test_rejects_alive_only_with_status_filters(self) -> None:
        with pytest.raises(pydantic.ValidationError, match="mutually exclusive"):
            subscriptions.ListSubscriptionsCommand(
                user_id=new_user_id(),
                statuses=[SubscriptionStatusId.active],
                alive_only=True,
            )


class TestRunAsyncCommand:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        called = False

        async def command() -> None:
            nonlocal called
            called = True

        await asyncio.to_thread(subscriptions.run_async_command, command())

        assert called

    @pytest.mark.asyncio
    async def test_project_error_exits_nonzero(self, capsys: pytest.CaptureFixture[str]) -> None:
        async def command() -> None:
            raise core_errors.CoreError(reason="invalid command")

        with pytest.raises(typer.Exit) as raised:
            await asyncio.to_thread(subscriptions.run_async_command, command())

        assert raised.value.exit_code == 1
        assert "CoreError" in capsys.readouterr().err

    @pytest.mark.asyncio
    async def test_stored_state_error_propagates(self) -> None:
        async def command() -> None:
            raise subscription_errors.InvalidStoredSubscription()

        with pytest.raises(subscription_errors.InvalidStoredSubscription):
            await asyncio.to_thread(subscriptions.run_async_command, command())

    @pytest.mark.asyncio
    async def test_unexpected_error_propagates(self) -> None:
        async def command() -> None:
            raise RuntimeError("unexpected command failure")

        with pytest.raises(RuntimeError, match="unexpected command failure"):
            await asyncio.to_thread(subscriptions.run_async_command, command())


class TestSubscriptionStatusFromName:
    @pytest.mark.parametrize("status", list(SubscriptionStatusId))
    def test_registered_name(self, status: SubscriptionStatusId) -> None:
        assert subscriptions.subscription_status_from_name(status.name) == status

    def test_rejects_numeric_value(self) -> None:
        with pytest.raises(typer.BadParameter):
            subscriptions.subscription_status_from_name(str(SubscriptionStatusId.active.value))

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(typer.BadParameter):
            subscriptions.subscription_status_from_name("")

    def test_rejects_unknown_name(self) -> None:
        with pytest.raises(typer.BadParameter):
            subscriptions.subscription_status_from_name("unknown")


class TestSubscriptionRecord:
    def test_serializes_subscription(self) -> None:
        started_at = datetime.datetime.now(tz=datetime.UTC)
        period_starts_at = started_at + datetime.timedelta(days=1)
        period_ends_at = period_starts_at + datetime.timedelta(days=30)
        expected_renewal_at = period_ends_at
        ends_at = period_ends_at + datetime.timedelta(days=1)
        subscription = make_subscription(
            status=SubscriptionStatusId.past_due,
            started_at=started_at,
            period_starts_at=period_starts_at,
            period_ends_at=period_ends_at,
            expected_renewal_at=expected_renewal_at,
            ends_at=ends_at,
            provider_updated_at=started_at + datetime.timedelta(seconds=1),
        )

        assert subscriptions.subscription_record(subscription) == {
            "id": str(subscription.id),
            "state_transaction_id": str(subscription.state_transaction_id),
            "user_id": str(subscription.user_id),
            "benefit_id": subscription.benefit_id,
            "status": "past_due",
            "status_id": 4,
            "provider_status": subscription.provider_status,
            "started_at": started_at.isoformat(),
            "period_starts_at": period_starts_at.isoformat(),
            "period_ends_at": period_ends_at.isoformat(),
            "expected_renewal_at": expected_renewal_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "provider_updated_at": subscription.provider_updated_at.isoformat(),
        }

    def test_serializes_missing_optional_timestamps(self) -> None:
        record = subscriptions.subscription_record(make_subscription())

        assert record["expected_renewal_at"] is None
        assert record["ends_at"] is None


class TestSubscriptionsTable:
    def test_renders_subscription_fields(self) -> None:
        started_at = datetime.datetime.now(tz=datetime.UTC)
        period_starts_at = started_at + datetime.timedelta(days=1)
        period_ends_at = period_starts_at + datetime.timedelta(days=30)
        expected_renewal_at = period_ends_at
        ends_at = period_ends_at + datetime.timedelta(days=1)
        subscription = make_subscription(
            status=SubscriptionStatusId.paused,
            provider_status=ProviderStatus("paused at provider"),
            started_at=started_at,
            period_starts_at=period_starts_at,
            period_ends_at=period_ends_at,
            expected_renewal_at=expected_renewal_at,
            ends_at=ends_at,
        )

        table = subscriptions.subscriptions_table([subscription])

        for value in (
            str(subscription.id),
            subscription.benefit_id,
            "paused",
            "paused at provider",
            started_at.isoformat(),
            period_starts_at.isoformat(),
            period_ends_at.isoformat(),
            expected_renewal_at.isoformat(),
            ends_at.isoformat(),
        ):
            assert value in table

    def test_renders_missing_optional_timestamps(self) -> None:
        table = subscriptions.subscriptions_table([make_subscription()])

        assert table.count(" - ") == 2


class TestRunList:
    @pytest.mark.asyncio
    async def test_outputs_domain_result_as_table(
        self,
        mocker: MockerFixture,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mocker.patch.object(subscriptions, "with_app", return_value=contextlib.nullcontext())
        user_id = new_user_id()
        stored = [make_subscription(user_id=user_id), make_subscription(user_id=user_id)]
        received: list[tuple[UserId, list[SubscriptionStatusId] | None]] = []

        async def get_subscriptions(
            selected_user_id: UserId,
            *,
            statuses: list[SubscriptionStatusId] | None = None,
        ) -> list[Subscription]:
            received.append((selected_user_id, statuses))
            return stored

        mocker.patch.object(
            subscriptions.s_domain,
            "get_subscriptions_for_user",
            side_effect=get_subscriptions,
        )

        await subscriptions.run_list(subscriptions.ListSubscriptionsCommand(user_id=user_id))

        assert received == [(user_id, None)]
        assert capsys.readouterr().out == subscriptions.subscriptions_table(stored) + "\n"

    @pytest.mark.asyncio
    async def test_json_output_uses_json_lines(
        self,
        mocker: MockerFixture,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mocker.patch.object(subscriptions, "with_app", return_value=contextlib.nullcontext())
        user_id = new_user_id()
        stored = [make_subscription(user_id=user_id), make_subscription(user_id=user_id)]
        mocker.patch.object(
            subscriptions.s_domain,
            "get_subscriptions_for_user",
            return_value=stored,
        )

        await subscriptions.run_list(subscriptions.ListSubscriptionsCommand(user_id=user_id, json_output=True))

        assert capsys.readouterr().out.splitlines() == [
            json.dumps(subscriptions.subscription_record(subscription)) for subscription in stored
        ]

    @pytest.mark.asyncio
    async def test_passes_status_filters_to_domain(self, mocker: MockerFixture) -> None:
        mocker.patch.object(subscriptions, "with_app", return_value=contextlib.nullcontext())
        user_id = new_user_id()
        statuses = [SubscriptionStatusId.active, SubscriptionStatusId.paused]
        received: list[tuple[UserId, list[SubscriptionStatusId] | None]] = []

        async def get_subscriptions(
            selected_user_id: UserId,
            *,
            statuses: list[SubscriptionStatusId] | None = None,
        ) -> list[Subscription]:
            received.append((selected_user_id, statuses))
            return []

        mocker.patch.object(
            subscriptions.s_domain,
            "get_subscriptions_for_user",
            side_effect=get_subscriptions,
        )

        await subscriptions.run_list(subscriptions.ListSubscriptionsCommand(user_id=user_id, statuses=statuses))

        assert received == [(user_id, statuses)]

    @pytest.mark.asyncio
    async def test_alive_only_uses_alive_query(self, mocker: MockerFixture) -> None:
        mocker.patch.object(subscriptions, "with_app", return_value=contextlib.nullcontext())
        user_id = new_user_id()
        received: list[UserId] = []

        async def get_alive_subscriptions(selected_user_id: UserId) -> list[Subscription]:
            received.append(selected_user_id)
            return []

        async def get_subscriptions(*_: object, **__: object) -> list[Subscription]:
            raise AssertionError("regular subscription query must not be called")

        mocker.patch.object(
            subscriptions.s_domain,
            "get_alive_subscriptions_for_user",
            side_effect=get_alive_subscriptions,
        )
        mocker.patch.object(
            subscriptions.s_domain,
            "get_subscriptions_for_user",
            side_effect=get_subscriptions,
        )

        await subscriptions.run_list(subscriptions.ListSubscriptionsCommand(user_id=user_id, alive_only=True))

        assert received == [user_id]


class TestListSubscriptions:
    @pytest.mark.asyncio
    async def test_builds_and_runs_command(self, mocker: MockerFixture) -> None:
        received: list[subscriptions.ListSubscriptionsCommand] = []

        async def run_list(command: subscriptions.ListSubscriptionsCommand) -> None:
            received.append(command)

        mocker.patch.object(subscriptions, "run_list", side_effect=run_list)
        user_id = new_user_id()

        await asyncio.to_thread(
            subscriptions.list_subscriptions,
            user_id=user_id,
            statuses=["active", "paused"],
            alive=False,
            json_output=True,
        )

        assert received == [
            subscriptions.ListSubscriptionsCommand(
                user_id=UserId(user_id),
                statuses=[SubscriptionStatusId.active, SubscriptionStatusId.paused],
                json_output=True,
            )
        ]

    def test_rejects_status_filters_with_alive(self) -> None:
        with pytest.raises(typer.BadParameter, match="invalid list parameters"):
            subscriptions.list_subscriptions(
                user_id=new_user_id(),
                statuses=["active"],
                alive=True,
                json_output=False,
            )
