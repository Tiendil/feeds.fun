import asyncio
import contextlib
import datetime
import json

import pydantic
import pytest
import typer
from pytest_mock import MockerFixture

from ffun.audit.entities import AuditEntityKind
from ffun.cli.commands import subscriptions
from ffun.core import errors as core_errors
from ffun.domain.domain import new_user_id
from ffun.domain.entities import SerializedId, UserId
from ffun.subscriptions import errors as subscription_errors
from ffun.subscriptions.entities import (
    ProviderStatus,
    SaveSubscriptionOutcome,
    Subscription,
    SubscriptionStatusId,
)
from ffun.subscriptions.tests.make import make_subscription


def make_update_command(subscription: Subscription, **changes: object) -> subscriptions.UpdateSubscriptionCommand:
    data: dict[str, object] = {
        "user_id": subscription.user_id,
        "provider_id": subscription.provider_id,
        "provider_merchant_id": subscription.provider_merchant_id,
        "provider_subscription_id": subscription.provider_subscription_id,
        "provider_status": ProviderStatus("updated"),
        "provider_updated_at": subscription.provider_updated_at + datetime.timedelta(seconds=1),
        "actor_kind": AuditEntityKind.admin,
        "actor_id": SerializedId("test-admin"),
    }
    data.update(changes)
    return subscriptions.UpdateSubscriptionCommand.model_validate(data)


class TestUpdateSubscriptionCommand:
    def test_accepts_one_change(self) -> None:
        subscription = make_subscription()

        command = make_update_command(subscription)

        assert command.provider_status == "updated"

    def test_rejects_missing_change(self) -> None:
        subscription = make_subscription()

        with pytest.raises(pydantic.ValidationError, match="at least one subscription field"):
            make_update_command(subscription, provider_status=None)

    def test_rejects_renewal_value_and_clear(self) -> None:
        subscription = make_subscription()

        with pytest.raises(pydantic.ValidationError, match="renews_at and clear_renews_at"):
            make_update_command(
                subscription,
                renews_at=subscription.started_at,
                clear_renews_at=True,
            )

    def test_rejects_end_value_and_clear(self) -> None:
        subscription = make_subscription()

        with pytest.raises(pydantic.ValidationError, match="ends_at and clear_ends_at"):
            make_update_command(
                subscription,
                ends_at=subscription.started_at,
                clear_ends_at=True,
            )


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

    def test_rejects_unknown_name(self) -> None:
        with pytest.raises(typer.BadParameter):
            subscriptions.subscription_status_from_name("unknown")


class TestActorKindFromName:
    @pytest.mark.parametrize("kind", list(AuditEntityKind))
    def test_registered_name(self, kind: AuditEntityKind) -> None:
        assert subscriptions.actor_kind_from_name(kind.name) == kind

    def test_rejects_unknown_name(self) -> None:
        with pytest.raises(typer.BadParameter):
            subscriptions.actor_kind_from_name("unknown")


class TestTimestampFromString:
    def test_missing_value(self) -> None:
        assert subscriptions.timestamp_from_string(None, option_name="--started-at") is None

    def test_iso_8601_with_utc_offset(self) -> None:
        timestamp = datetime.datetime.now(tz=datetime.timezone(datetime.timedelta(hours=2)))

        assert subscriptions.timestamp_from_string(timestamp.isoformat(), option_name="--started-at") == timestamp

    def test_rejects_invalid_value(self) -> None:
        with pytest.raises(typer.BadParameter):
            subscriptions.timestamp_from_string("not-a-timestamp", option_name="--started-at")

    def test_rejects_value_without_utc_offset(self) -> None:
        timestamp = datetime.datetime.now()

        with pytest.raises(typer.BadParameter):
            subscriptions.timestamp_from_string(timestamp.isoformat(), option_name="--started-at")


class TestSubscriptionRecord:
    def test_serializes_subscription(self) -> None:
        started_at = datetime.datetime.now(tz=datetime.UTC)
        renews_at = started_at + datetime.timedelta(days=30)
        ends_at = renews_at + datetime.timedelta(days=1)
        subscription = make_subscription(
            status=SubscriptionStatusId.past_due,
            started_at=started_at,
            renews_at=renews_at,
            ends_at=ends_at,
            provider_updated_at=started_at + datetime.timedelta(seconds=1),
        )

        assert subscriptions.subscription_record(subscription) == {
            "provider_id": subscription.provider_id,
            "provider_merchant_id": subscription.provider_merchant_id,
            "provider_subscription_id": subscription.provider_subscription_id,
            "user_id": str(subscription.user_id),
            "provider_customer_id": subscription.provider_customer_id,
            "status": "past_due",
            "status_id": 4,
            "provider_status": subscription.provider_status,
            "started_at": started_at.isoformat(),
            "renews_at": renews_at.isoformat(),
            "ends_at": ends_at.isoformat(),
            "provider_updated_at": subscription.provider_updated_at.isoformat(),
        }

    def test_serializes_missing_optional_timestamps(self) -> None:
        subscription = make_subscription()

        record = subscriptions.subscription_record(subscription)

        assert record["renews_at"] is None
        assert record["ends_at"] is None


class TestSubscriptionsTable:
    def test_renders_subscription_fields(self) -> None:
        started_at = datetime.datetime.now(tz=datetime.UTC)
        renews_at = started_at + datetime.timedelta(days=30)
        ends_at = renews_at + datetime.timedelta(days=1)
        subscription = make_subscription(
            status=SubscriptionStatusId.paused,
            provider_status=ProviderStatus("paused at provider"),
            started_at=started_at,
            renews_at=renews_at,
            ends_at=ends_at,
        )

        table = subscriptions.subscriptions_table([subscription])

        for value in (
            "provider",
            "merchant",
            "subscription",
            "customer",
            "paused",
            "paused at provider",
            started_at.isoformat(),
            renews_at.isoformat(),
            ends_at.isoformat(),
        ):
            assert value in table

    def test_renders_missing_optional_timestamps(self) -> None:
        table = subscriptions.subscriptions_table([make_subscription()])

        assert table.count(" - ") == 2


class TestSubscriptionChangeOutput:
    def test_human_output(self) -> None:
        subscription = make_subscription()

        assert (
            subscriptions.subscription_change_output(
                SaveSubscriptionOutcome.created,
                subscription,
                json_output=False,
            )
            == f"Created subscription snapshot\n{subscriptions.subscriptions_table([subscription])}"
        )

    def test_json_output(self) -> None:
        subscription = make_subscription()
        expected: dict[str, object] = {
            "outcome": "updated",
            "outcome_id": 2,
            "subscription": subscriptions.subscription_record(subscription),
        }

        assert subscriptions.subscription_change_output(
            SaveSubscriptionOutcome.updated,
            subscription,
            json_output=True,
        ) == json.dumps(expected)


class TestRunSet:
    @pytest.mark.asyncio
    async def test_saves_subscription_and_outputs_outcome(
        self,
        mocker: MockerFixture,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mocker.patch.object(subscriptions, "with_app", return_value=contextlib.nullcontext())
        subscription = make_subscription()
        received: list[tuple[Subscription, AuditEntityKind, SerializedId]] = []

        async def save_subscription(
            value: Subscription,
            *,
            actor_kind: AuditEntityKind,
            actor_id: SerializedId,
        ) -> SaveSubscriptionOutcome:
            received.append((value, actor_kind, actor_id))
            return SaveSubscriptionOutcome.created

        mocker.patch.object(subscriptions.s_domain, "save_subscription", side_effect=save_subscription)
        command = subscriptions.SetSubscriptionCommand(
            subscription=subscription,
            actor_kind=AuditEntityKind.admin,
            actor_id=SerializedId("test-admin"),
        )

        await subscriptions.run_set(command)

        assert received == [(subscription, command.actor_kind, command.actor_id)]
        assert (
            capsys.readouterr().out
            == subscriptions.subscription_change_output(
                SaveSubscriptionOutcome.created,
                subscription,
                json_output=False,
            )
            + "\n"
        )


class TestUpdatedSubscription:
    def test_replaces_selected_fields_and_preserves_others(self) -> None:
        subscription = make_subscription()
        command = make_update_command(
            subscription,
            status=SubscriptionStatusId.paused,
            provider_status=ProviderStatus("paused by provider"),
            started_at=subscription.started_at + datetime.timedelta(days=1),
        )

        updated = subscriptions.updated_subscription(subscription, command)

        assert updated == subscription.replace(
            status=SubscriptionStatusId.paused,
            provider_status=ProviderStatus("paused by provider"),
            started_at=command.started_at,
            provider_updated_at=command.provider_updated_at,
        )

    def test_replaces_optional_timestamps(self) -> None:
        subscription = make_subscription()
        renews_at = subscription.started_at + datetime.timedelta(days=30)
        ends_at = renews_at + datetime.timedelta(days=1)
        command = make_update_command(subscription, renews_at=renews_at, ends_at=ends_at)

        updated = subscriptions.updated_subscription(subscription, command)

        assert updated.renews_at == renews_at
        assert updated.ends_at == ends_at

    def test_clears_optional_timestamps(self) -> None:
        timestamp = datetime.datetime.now(tz=datetime.UTC)
        subscription = make_subscription(renews_at=timestamp, ends_at=timestamp)
        command = make_update_command(subscription, clear_renews_at=True, clear_ends_at=True)

        updated = subscriptions.updated_subscription(subscription, command)

        assert updated.renews_at is None
        assert updated.ends_at is None


class TestRunUpdate:
    @pytest.mark.asyncio
    async def test_updates_subscription_and_outputs_outcome(
        self,
        mocker: MockerFixture,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mocker.patch.object(subscriptions, "with_app", return_value=contextlib.nullcontext())
        subscription = make_subscription()
        command = make_update_command(subscription, status=SubscriptionStatusId.ended)
        received: list[tuple[Subscription, AuditEntityKind, SerializedId]] = []

        mocker.patch.object(subscriptions.s_domain, "get_subscription", return_value=subscription)

        async def save_subscription(
            value: Subscription,
            *,
            actor_kind: AuditEntityKind,
            actor_id: SerializedId,
        ) -> SaveSubscriptionOutcome:
            received.append((value, actor_kind, actor_id))
            return SaveSubscriptionOutcome.updated

        mocker.patch.object(subscriptions.s_domain, "save_subscription", side_effect=save_subscription)

        await subscriptions.run_update(command)

        assert received == [
            (
                subscriptions.updated_subscription(subscription, command),
                command.actor_kind,
                command.actor_id,
            )
        ]
        result_subscription = subscriptions.updated_subscription(subscription, command)
        assert (
            capsys.readouterr().out
            == subscriptions.subscription_change_output(
                SaveSubscriptionOutcome.updated,
                result_subscription,
                json_output=False,
            )
            + "\n"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("different_owner", [False, True])
    async def test_rejects_missing_or_different_user_subscription(
        self,
        mocker: MockerFixture,
        different_owner: bool,
    ) -> None:
        mocker.patch.object(subscriptions, "with_app", return_value=contextlib.nullcontext())
        subscription = make_subscription()
        command = make_update_command(subscription)
        stored = subscription.replace(user_id=new_user_id()) if different_owner else None
        mocker.patch.object(subscriptions.s_domain, "get_subscription", return_value=stored)

        with pytest.raises(typer.BadParameter, match="not found for the specified user"):
            await subscriptions.run_update(command)


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


class TestSetSubscription:
    @pytest.mark.asyncio
    async def test_resolves_default_parameters(self, mocker: MockerFixture) -> None:
        received: list[subscriptions.SetSubscriptionCommand] = []

        async def run_set(command: subscriptions.SetSubscriptionCommand) -> None:
            received.append(command)

        mocker.patch.object(subscriptions, "run_set", side_effect=run_set)
        user_id = new_user_id()
        called_at = datetime.datetime.now(tz=datetime.UTC)

        await asyncio.to_thread(
            subscriptions.set_subscription,
            user_id=user_id,
            provider_id=subscriptions.DEFAULT_PROVIDER_ID,
            provider_merchant_id=None,
            provider_subscription_id=None,
            provider_customer_id=None,
            status="active",
            provider_status=None,
            started_at=None,
            renews_at=None,
            ends_at=None,
            provider_updated_at=None,
            json_output=False,
            actor_kind="admin",
            actor_id="admin",
        )

        finished_at = datetime.datetime.now(tz=datetime.UTC)
        assert len(received) == 1
        command = received[0]
        subscription = command.subscription
        assert subscription.provider_id == "feeds-fun-cli"
        assert subscription.provider_merchant_id == "feeds-fun"
        assert subscription.provider_subscription_id == f"feeds-fun-subscription-{user_id}"
        assert subscription.provider_customer_id == f"feeds-fun-user-{user_id}"
        assert subscription.status == SubscriptionStatusId.active
        assert subscription.provider_status == "active"
        assert called_at <= subscription.started_at <= finished_at
        assert subscription.renews_at is None
        assert subscription.ends_at == subscription.started_at + subscriptions.DEFAULT_SUBSCRIPTION_DURATION
        assert subscription.provider_updated_at == subscription.started_at
        assert command.actor_kind == AuditEntityKind.admin
        assert command.actor_id == "admin"

    @pytest.mark.asyncio
    async def test_dependent_defaults_follow_explicit_values(self, mocker: MockerFixture) -> None:
        received: list[subscriptions.SetSubscriptionCommand] = []

        async def run_set(command: subscriptions.SetSubscriptionCommand) -> None:
            received.append(command)

        mocker.patch.object(subscriptions, "run_set", side_effect=run_set)
        started_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=5)

        await asyncio.to_thread(
            subscriptions.set_subscription,
            user_id=new_user_id(),
            provider_id=subscriptions.DEFAULT_PROVIDER_ID,
            provider_merchant_id=None,
            provider_subscription_id=None,
            provider_customer_id=None,
            status="paused",
            provider_status=None,
            started_at=started_at.isoformat(),
            renews_at=None,
            ends_at=None,
            provider_updated_at=None,
            json_output=False,
            actor_kind="admin",
            actor_id="admin",
        )

        assert len(received) == 1
        subscription = received[0].subscription
        assert subscription.provider_status == "paused"
        assert subscription.started_at == started_at
        assert subscription.ends_at == started_at + subscriptions.DEFAULT_SUBSCRIPTION_DURATION

    @pytest.mark.asyncio
    async def test_builds_and_runs_command(self, mocker: MockerFixture) -> None:
        received: list[subscriptions.SetSubscriptionCommand] = []

        async def run_set(command: subscriptions.SetSubscriptionCommand) -> None:
            received.append(command)

        mocker.patch.object(subscriptions, "run_set", side_effect=run_set)
        started_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        called_at = datetime.datetime.now(tz=datetime.UTC)

        await asyncio.to_thread(
            subscriptions.set_subscription,
            user_id=new_user_id(),
            provider_id="provider",
            provider_merchant_id="merchant",
            provider_subscription_id="subscription",
            provider_customer_id="customer",
            status="active",
            provider_status="active at provider",
            started_at=started_at.isoformat(),
            renews_at=None,
            ends_at=None,
            provider_updated_at=None,
            json_output=True,
            actor_kind="admin",
            actor_id="test-admin",
        )

        finished_at = datetime.datetime.now(tz=datetime.UTC)
        assert len(received) == 1
        command = received[0]
        assert called_at <= command.subscription.provider_updated_at <= finished_at
        assert command.subscription.started_at == started_at
        assert command.subscription.ends_at == started_at + subscriptions.DEFAULT_SUBSCRIPTION_DURATION
        assert command.subscription.status == SubscriptionStatusId.active
        assert command.actor_id == "test-admin"
        assert command.json_output

    @pytest.mark.parametrize(
        "missing_field",
        ["provider_merchant_id", "provider_subscription_id", "provider_customer_id"],
    )
    def test_nondefault_provider_requires_explicit_identity(self, missing_field: str) -> None:
        values: dict[str, object] = {
            "user_id": new_user_id(),
            "provider_id": "provider",
            "provider_merchant_id": "merchant",
            "provider_subscription_id": "subscription",
            "provider_customer_id": "customer",
            "status": "active",
            "provider_status": None,
            "started_at": None,
            "renews_at": None,
            "ends_at": None,
            "provider_updated_at": None,
            "json_output": False,
            "actor_kind": "admin",
            "actor_id": "admin",
        }
        values[missing_field] = None

        with pytest.raises(typer.BadParameter, match="requires explicit provider identity options"):
            subscriptions.set_subscription(**values)  # type: ignore[arg-type]

    def test_rejects_invalid_parameters(self) -> None:
        started_at = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(typer.BadParameter, match="invalid set parameters"):
            subscriptions.set_subscription(
                user_id=new_user_id(),
                provider_id=" ",
                provider_merchant_id="merchant",
                provider_subscription_id="subscription",
                provider_customer_id="customer",
                status="active",
                provider_status="active",
                started_at=started_at.isoformat(),
                renews_at=None,
                ends_at=None,
                provider_updated_at=None,
                json_output=False,
                actor_kind="admin",
                actor_id="test-admin",
            )


class TestUpdateSubscription:
    @pytest.mark.asyncio
    async def test_builds_and_runs_command(self, mocker: MockerFixture) -> None:
        received: list[subscriptions.UpdateSubscriptionCommand] = []

        async def run_update(command: subscriptions.UpdateSubscriptionCommand) -> None:
            received.append(command)

        mocker.patch.object(subscriptions, "run_update", side_effect=run_update)
        called_at = datetime.datetime.now(tz=datetime.UTC)

        await asyncio.to_thread(
            subscriptions.update_subscription,
            user_id=new_user_id(),
            provider_id="provider",
            provider_merchant_id="merchant",
            provider_subscription_id="subscription",
            status="ended",
            provider_status=None,
            started_at=None,
            renews_at=None,
            clear_renews_at=False,
            ends_at=None,
            clear_ends_at=True,
            provider_updated_at=None,
            json_output=True,
            actor_kind="admin",
            actor_id="test-admin",
        )

        finished_at = datetime.datetime.now(tz=datetime.UTC)
        assert len(received) == 1
        command = received[0]
        assert command.status == SubscriptionStatusId.ended
        assert command.clear_ends_at
        assert command.json_output
        assert called_at <= command.provider_updated_at <= finished_at

    def test_rejects_missing_change(self) -> None:
        with pytest.raises(typer.BadParameter, match="invalid update parameters"):
            subscriptions.update_subscription(
                user_id=new_user_id(),
                provider_id="provider",
                provider_merchant_id="merchant",
                provider_subscription_id="subscription",
                status=None,
                provider_status=None,
                started_at=None,
                renews_at=None,
                clear_renews_at=False,
                ends_at=None,
                clear_ends_at=False,
                provider_updated_at=None,
                json_output=False,
                actor_kind="admin",
                actor_id="test-admin",
            )


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
