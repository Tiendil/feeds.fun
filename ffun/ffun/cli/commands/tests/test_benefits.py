import asyncio
import contextlib
import datetime
import json
import uuid

import pytest
import typer
from pytest_mock import MockerFixture

from ffun.audit.entities import AuditEntityKind
from ffun.benefits.entities import (
    ADMIN_BENEFIT_SOURCE_ID,
    BenefitParameterId,
    BenefitSourceTransactionId,
    BenefitTransactionApplicationResult,
    InternalTarget,
    NewTarget,
)
from ffun.benefits.tests.make import (
    make_one_time_purchase_transaction_command,
    make_subscription_snapshot,
    make_transaction_command,
)
from ffun.cli.commands import benefits
from ffun.core import errors as core_errors
from ffun.domain.entities import (
    BenefitId,
    BenefitTransactionId,
    OneTimePurchaseId,
    ProviderStatus,
    SerializedId,
    SubscriptionId,
    UserId,
)
from ffun.one_time_purchases.entities import PurchaseStatus
from ffun.one_time_purchases.tests.make import make_purchase_snapshot
from ffun.subscriptions.entities import SubscriptionStatusId


class TestOptionOrCreationDefault:
    def test_provided_value(self) -> None:
        assert (
            benefits.option_or_creation_default(
                "provided",
                target_id=uuid.uuid4(),
                option_name="--value",
                creation_default="default",
            )
            == "provided"
        )

    def test_new_target_uses_creation_default(self) -> None:
        assert (
            benefits.option_or_creation_default(
                None,
                target_id=None,
                option_name="--value",
                creation_default="default",
            )
            == "default"
        )

    def test_existing_target_requires_value(self) -> None:
        with pytest.raises(
            typer.BadParameter, match="--value is required when applying a snapshot to an existing target"
        ):
            benefits.option_or_creation_default(
                None,
                target_id=uuid.uuid4(),
                option_name="--value",
                creation_default="default",
            )


class TestRunAsyncCommand:
    @pytest.mark.asyncio
    async def test_success(self) -> None:
        called = False

        async def command() -> None:
            nonlocal called
            called = True

        await asyncio.to_thread(benefits.run_async_command, command())

        assert called

    @pytest.mark.asyncio
    async def test_project_error_exits_nonzero(self, capsys: pytest.CaptureFixture[str]) -> None:
        async def command() -> None:
            raise core_errors.CoreError(reason="invalid command")

        with pytest.raises(typer.Exit) as raised:
            await asyncio.to_thread(benefits.run_async_command, command())

        assert raised.value.exit_code == 1
        assert "CoreError" in capsys.readouterr().err

    @pytest.mark.asyncio
    async def test_unexpected_error_propagates(self) -> None:
        async def command() -> None:
            raise RuntimeError("unexpected command failure")

        with pytest.raises(RuntimeError, match="unexpected command failure"):
            await asyncio.to_thread(benefits.run_async_command, command())


class TestBenefitParametersFromOptions:
    def test_empty(self) -> None:
        assert benefits.benefit_parameters_from_options([]) == {}

    def test_normalizes_names_and_integer_values(self) -> None:
        assert benefits.benefit_parameters_from_options([" quantity = 500", "bonus=25"]) == {
            BenefitParameterId("quantity"): 500,
            BenefitParameterId("bonus"): 25,
        }

    @pytest.mark.parametrize("option", ["quantity", "=10", "quantity=not-an-integer"])
    def test_rejects_invalid_option(self, option: str) -> None:
        with pytest.raises(typer.BadParameter, match="expected NAME=INTEGER"):
            benefits.benefit_parameters_from_options([option])

    def test_rejects_duplicate_normalized_name(self) -> None:
        with pytest.raises(typer.BadParameter, match="duplicate benefit parameter"):
            benefits.benefit_parameters_from_options(["quantity=10", " quantity =20"])


class TestPurchaseStatusFromName:
    @pytest.mark.parametrize("status", list(PurchaseStatus))
    def test_registered_name(self, status: PurchaseStatus) -> None:
        assert benefits.purchase_status_from_name(status.name) == status

    @pytest.mark.parametrize("raw_status", ["", "unknown", str(PurchaseStatus.completed.value)])
    def test_rejects_unknown_name(self, raw_status: str) -> None:
        with pytest.raises(typer.BadParameter):
            benefits.purchase_status_from_name(raw_status)


class TestRunApplySubscription:
    @pytest.mark.asyncio
    async def test_submits_normalized_inputs_as_administrator(
        self,
        mocker: MockerFixture,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mocker.patch.object(benefits, "with_app", return_value=contextlib.nullcontext())
        snapshot = make_subscription_snapshot()
        parameters = {BenefitParameterId("quantity"): 100}
        transaction = make_transaction_command()
        actor_id = SerializedId("administrator@example.com")
        result = BenefitTransactionApplicationResult[SubscriptionId](
            transaction_id=BenefitTransactionId(uuid.uuid4()),
            transaction_created=True,
            target_id=SubscriptionId(uuid.uuid4()),
        )
        apply = mocker.patch.object(
            benefits.benefits_domain,
            "apply_subscription_transaction",
            return_value=result,
        )

        await benefits.run_apply_subscription(snapshot, parameters, transaction, actor_id)

        apply.assert_awaited_once_with(
            snapshot,
            parameters,
            transaction,
            actor_kind=AuditEntityKind.admin,
            actor_id=actor_id,
        )
        expected_payload: dict[str, object] = {
            "transaction_id": str(result.transaction_id),
            "transaction_created": result.transaction_created,
            "target_id": str(result.target_id),
            "source_transaction_id": str(transaction.source_transaction_id),
        }
        assert capsys.readouterr().out == json.dumps(expected_payload) + "\n"


class TestRunApplyOneTimePurchase:
    @pytest.mark.asyncio
    async def test_submits_normalized_inputs_as_administrator(
        self,
        mocker: MockerFixture,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        mocker.patch.object(benefits, "with_app", return_value=contextlib.nullcontext())
        snapshot = make_purchase_snapshot()
        parameters = {BenefitParameterId("quantity"): 100}
        transaction = make_one_time_purchase_transaction_command()
        actor_id = SerializedId("administrator@example.com")
        result = BenefitTransactionApplicationResult[OneTimePurchaseId](
            transaction_id=BenefitTransactionId(uuid.uuid4()),
            transaction_created=True,
            target_id=OneTimePurchaseId(uuid.uuid4()),
        )
        apply = mocker.patch.object(
            benefits.benefits_domain,
            "apply_one_time_purchase_transaction",
            return_value=result,
        )

        await benefits.run_apply_one_time_purchase(snapshot, parameters, transaction, actor_id)

        apply.assert_awaited_once_with(
            snapshot,
            parameters,
            transaction,
            actor_kind=AuditEntityKind.admin,
            actor_id=actor_id,
        )
        expected_payload: dict[str, object] = {
            "transaction_id": str(result.transaction_id),
            "transaction_created": result.transaction_created,
            "target_id": str(result.target_id),
            "source_transaction_id": str(transaction.source_transaction_id),
        }
        assert capsys.readouterr().out == json.dumps(expected_payload) + "\n"


class TestApplySubscription:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("selected_subscription_id", [None, uuid.uuid4()])
    async def test_builds_and_runs_normalized_command(
        self,
        selected_subscription_id: uuid.UUID | None,
        mocker: MockerFixture,
    ) -> None:
        received: list[
            tuple[
                object,
                object,
                object,
                SerializedId,
            ]
        ] = []

        async def run_apply_subscription(
            snapshot: object,
            parameters: object,
            transaction: object,
            actor_id: SerializedId,
        ) -> None:
            received.append((snapshot, parameters, transaction, actor_id))

        mocker.patch.object(benefits, "run_apply_subscription", side_effect=run_apply_subscription)
        now = datetime.datetime.now(tz=datetime.UTC)
        mocker.patch.object(benefits.core_utils, "now", return_value=now)
        user_id = uuid.uuid4()
        source_transaction_id = uuid.uuid4()

        await asyncio.to_thread(
            benefits.apply_subscription,
            user_id=user_id,
            benefit_id="supporter",
            status="active",
            provider_status="active-at-provider",
            started_at=now - datetime.timedelta(days=30),
            period_starts_at=now - datetime.timedelta(days=1),
            period_ends_at=now + datetime.timedelta(days=29),
            provider_updated_at=now,
            source_transaction_id=source_transaction_id,
            actor_id="administrator@example.com",
            parameters=["quantity=500"],
            subscription_id=selected_subscription_id,
            expected_renewal_at=now + datetime.timedelta(days=29),
            ends_at=None,
        )

        assert len(received) == 1
        snapshot, parameters, transaction, actor_id = received[0]
        assert snapshot == make_subscription_snapshot(
            user_id=UserId(user_id),
            benefit_id=BenefitId("supporter"),
            status=SubscriptionStatusId.active,
            provider_status="active-at-provider",
            started_at=now - datetime.timedelta(days=30),
            period_starts_at=now - datetime.timedelta(days=1),
            period_ends_at=now + datetime.timedelta(days=29),
            expected_renewal_at=now + datetime.timedelta(days=29),
            provider_updated_at=now,
        )
        assert parameters == {BenefitParameterId("quantity"): 500}
        assert transaction == make_transaction_command(
            source_id=ADMIN_BENEFIT_SOURCE_ID,
            source_transaction_id=BenefitSourceTransactionId(source_transaction_id),
            target=(
                InternalTarget(internal_id=SubscriptionId(selected_subscription_id))
                if selected_subscription_id is not None
                else NewTarget()
            ),
            effective_at=now,
        )
        assert actor_id == SerializedId("administrator@example.com")

    def test_rejects_invalid_snapshot(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(typer.BadParameter, match="invalid subscription benefit parameters"):
            benefits.apply_subscription(
                user_id=uuid.uuid4(),
                benefit_id="supporter",
                status="active",
                provider_status="active",
                started_at=now.replace(tzinfo=None),
                period_starts_at=now,
                period_ends_at=now + datetime.timedelta(days=1),
                provider_updated_at=now,
                source_transaction_id=uuid.uuid4(),
                actor_id="administrator@example.com",
                parameters=[],
                subscription_id=None,
                expected_renewal_at=None,
                ends_at=None,
            )


class TestApplyOneTimePurchase:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("selected_purchase_id", [None, uuid.uuid4()])
    async def test_builds_and_runs_normalized_command(
        self,
        selected_purchase_id: uuid.UUID | None,
        mocker: MockerFixture,
    ) -> None:
        received: list[tuple[object, object, object, SerializedId]] = []

        async def run_apply_one_time_purchase(
            snapshot: object,
            parameters: object,
            transaction: object,
            actor_id: SerializedId,
        ) -> None:
            received.append((snapshot, parameters, transaction, actor_id))

        mocker.patch.object(benefits, "run_apply_one_time_purchase", side_effect=run_apply_one_time_purchase)
        now = datetime.datetime.now(tz=datetime.UTC)
        mocker.patch.object(benefits.core_utils, "now", return_value=now)
        user_id = uuid.uuid4()
        source_transaction_id = uuid.uuid4()

        await asyncio.to_thread(
            benefits.apply_one_time_purchase,
            user_id=user_id,
            benefit_id="lifetime-tokens",
            status="completed",
            provider_status="paid",
            purchased_at=now - datetime.timedelta(days=1),
            provider_updated_at=now,
            source_transaction_id=source_transaction_id,
            actor_id="administrator@example.com",
            parameters=["quantity=500"],
            one_time_purchase_id=selected_purchase_id,
        )

        assert len(received) == 1
        snapshot, parameters, transaction, actor_id = received[0]
        assert snapshot == make_purchase_snapshot(
            user_id=UserId(user_id),
            benefit_id=BenefitId("lifetime-tokens"),
            status=PurchaseStatus.completed,
            provider_status=ProviderStatus("paid"),
            purchased_at=now - datetime.timedelta(days=1),
            provider_updated_at=now,
        )
        assert parameters == {BenefitParameterId("quantity"): 500}
        assert transaction == make_one_time_purchase_transaction_command(
            source_id=ADMIN_BENEFIT_SOURCE_ID,
            source_transaction_id=BenefitSourceTransactionId(source_transaction_id),
            target=(
                InternalTarget(internal_id=OneTimePurchaseId(selected_purchase_id))
                if selected_purchase_id is not None
                else NewTarget()
            ),
            effective_at=now,
        )
        assert actor_id == SerializedId("administrator@example.com")

    def test_rejects_invalid_snapshot(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(typer.BadParameter, match="invalid one-time-purchase benefit parameters"):
            benefits.apply_one_time_purchase(
                user_id=uuid.uuid4(),
                benefit_id="lifetime-tokens",
                status="completed",
                provider_status="paid",
                purchased_at=now.replace(tzinfo=None),
                provider_updated_at=now,
                source_transaction_id=uuid.uuid4(),
                actor_id="administrator@example.com",
                parameters=["quantity=500"],
                one_time_purchase_id=None,
            )
