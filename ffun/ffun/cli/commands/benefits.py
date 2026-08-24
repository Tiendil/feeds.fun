import asyncio
import datetime
import json
import uuid
from collections.abc import Coroutine
from typing import TypeVar

import pydantic
import typer

from ffun.application.application import with_app
from ffun.audit.entities import AuditEntityKind
from ffun.benefits import domain as benefits_domain
from ffun.benefits.entities import (
    ADMIN_BENEFIT_SOURCE_ID,
    BenefitParameterId,
    BenefitParameters,
    BenefitSourceTransactionId,
    BenefitTransactionCommand,
    InternalTarget,
    NewTarget,
)
from ffun.cli.commands.subscriptions import subscription_status_from_name
from ffun.core import errors as core_errors
from ffun.core import utils as core_utils
from ffun.domain.entities import (
    BenefitId,
    OneTimePurchaseId,
    ProviderStatus,
    SerializedId,
    SubscriptionId,
    UserId,
)
from ffun.one_time_purchases.entities import PurchaseSnapshot, PurchaseStatus
from ffun.subscriptions.entities import SubscriptionSnapshot

cli_app = typer.Typer()

DEFAULT_ADMIN_ACTOR_ID = SerializedId("cli-admin")
DEFAULT_SUBSCRIPTION_PERIOD = datetime.timedelta(days=31)

ValueT = TypeVar("ValueT")


def option_or_creation_default(
    value: ValueT | None,
    *,
    target_id: uuid.UUID | None,
    option_name: str,
    creation_default: ValueT,
) -> ValueT:
    if value is not None:
        return value

    if target_id is not None:
        raise typer.BadParameter(f"{option_name} is required when applying a snapshot to an existing target")

    return creation_default


def run_async_command(command: Coroutine[object, object, None]) -> None:
    try:
        asyncio.run(command)
    except core_errors.Error as error:
        typer.echo(str(error), err=True)
        raise typer.Exit(code=1) from error


def benefit_parameters_from_options(options: list[str]) -> BenefitParameters:  # noqa: CCR001
    parameters: BenefitParameters = {}

    for option in options:
        raw_name, separator, raw_value = option.partition("=")
        normalized_name = raw_name.strip()

        if not separator or not normalized_name:
            raise typer.BadParameter(f"invalid benefit parameter {option!r}; expected NAME=INTEGER")

        parameter_id = BenefitParameterId(normalized_name)

        if parameter_id in parameters:
            raise typer.BadParameter(f"duplicate benefit parameter {parameter_id!r}")

        try:
            parameters[parameter_id] = int(raw_value.strip())
        except ValueError as error:
            raise typer.BadParameter(f"invalid benefit parameter {option!r}; expected NAME=INTEGER") from error

    return parameters


def purchase_status_from_name(raw_status: str) -> PurchaseStatus:
    try:
        return PurchaseStatus[raw_status]
    except KeyError as error:
        valid_names = ", ".join(status.name for status in PurchaseStatus)
        raise typer.BadParameter(
            f"unknown one-time purchase status {raw_status!r}; expected one of: {valid_names}"
        ) from error


async def run_apply_subscription(
    snapshot: SubscriptionSnapshot,
    parameters: BenefitParameters,
    transaction: BenefitTransactionCommand[SubscriptionId],
    actor_id: SerializedId,
) -> None:
    async with with_app():
        result = await benefits_domain.apply_subscription_transaction(
            snapshot,
            parameters,
            transaction,
            actor_kind=AuditEntityKind.admin,
            actor_id=actor_id,
        )

    payload: dict[str, object] = {
        "transaction_id": str(result.transaction_id),
        "transaction_created": result.transaction_created,
        "target_id": str(result.target_id),
        "source_transaction_id": str(transaction.source_transaction_id),
    }
    typer.echo(json.dumps(payload))


async def run_apply_one_time_purchase(
    snapshot: PurchaseSnapshot,
    parameters: BenefitParameters,
    transaction: BenefitTransactionCommand[OneTimePurchaseId],
    actor_id: SerializedId,
) -> None:
    async with with_app():
        result = await benefits_domain.apply_one_time_purchase_transaction(
            snapshot,
            parameters,
            transaction,
            actor_kind=AuditEntityKind.admin,
            actor_id=actor_id,
        )

    payload: dict[str, object] = {
        "transaction_id": str(result.transaction_id),
        "transaction_created": result.transaction_created,
        "target_id": str(result.target_id),
        "source_transaction_id": str(transaction.source_transaction_id),
    }
    typer.echo(json.dumps(payload))


@cli_app.command("apply-subscription")  # type: ignore[misc]
def apply_subscription(  # noqa: CFQ002
    user_id: uuid.UUID = typer.Option(..., "--user-id"),
    benefit_id: str = typer.Option(..., "--benefit-id"),
    status: str | None = typer.Option(None, "--status"),
    provider_status: str | None = typer.Option(None, "--provider-status"),
    started_at: datetime.datetime | None = typer.Option(None, "--started-at"),
    period_starts_at: datetime.datetime | None = typer.Option(None, "--period-starts-at"),
    period_ends_at: datetime.datetime | None = typer.Option(None, "--period-ends-at"),
    provider_updated_at: datetime.datetime | None = typer.Option(None, "--provider-updated-at"),
    source_transaction_id: uuid.UUID | None = typer.Option(None, "--source-transaction-id"),
    actor_id: str = typer.Option(str(DEFAULT_ADMIN_ACTOR_ID), "--actor-id"),
    parameters: list[str] | None = typer.Option(None, "--parameter"),
    subscription_id: uuid.UUID | None = typer.Option(None, "--subscription-id"),
    expected_renewal_at: datetime.datetime | None = typer.Option(None, "--expected-renewal-at"),
    ends_at: datetime.datetime | None = typer.Option(None, "--ends-at"),
) -> None:
    operation_time = core_utils.now()

    try:
        normalized_status = subscription_status_from_name(
            option_or_creation_default(
                status,
                target_id=subscription_id,
                option_name="--status",
                creation_default="active",
            )
        )
        snapshot = SubscriptionSnapshot(
            user_id=UserId(user_id),
            benefit_id=BenefitId(benefit_id),
            status=normalized_status,
            provider_status=ProviderStatus(
                option_or_creation_default(
                    provider_status,
                    target_id=subscription_id,
                    option_name="--provider-status",
                    creation_default=normalized_status.name,
                )
            ),
            started_at=option_or_creation_default(
                started_at,
                target_id=subscription_id,
                option_name="--started-at",
                creation_default=operation_time,
            ),
            period_starts_at=option_or_creation_default(
                period_starts_at,
                target_id=subscription_id,
                option_name="--period-starts-at",
                creation_default=operation_time,
            ),
            period_ends_at=option_or_creation_default(
                period_ends_at,
                target_id=subscription_id,
                option_name="--period-ends-at",
                creation_default=operation_time + DEFAULT_SUBSCRIPTION_PERIOD,
            ),
            expected_renewal_at=expected_renewal_at,
            ends_at=ends_at,
            provider_updated_at=option_or_creation_default(
                provider_updated_at,
                target_id=subscription_id,
                option_name="--provider-updated-at",
                creation_default=operation_time,
            ),
        )
        normalized_parameters = benefit_parameters_from_options(parameters or [])
        transaction = BenefitTransactionCommand[SubscriptionId](
            source_id=ADMIN_BENEFIT_SOURCE_ID,
            source_transaction_id=BenefitSourceTransactionId(source_transaction_id or uuid.uuid4()),
            target=(
                InternalTarget(internal_id=SubscriptionId(subscription_id))
                if subscription_id is not None
                else NewTarget()
            ),
            effective_at=operation_time,
        )
        normalized_actor_id = pydantic.TypeAdapter(SerializedId).validate_python(actor_id)
    except pydantic.ValidationError as error:
        raise typer.BadParameter("invalid subscription benefit parameters") from error

    run_async_command(run_apply_subscription(snapshot, normalized_parameters, transaction, normalized_actor_id))


@cli_app.command("apply-one-time-purchase")  # type: ignore[misc]
def apply_one_time_purchase(  # noqa: CFQ002
    user_id: uuid.UUID = typer.Option(..., "--user-id"),
    benefit_id: str = typer.Option(..., "--benefit-id"),
    status: str | None = typer.Option(None, "--status"),
    provider_status: str | None = typer.Option(None, "--provider-status"),
    purchased_at: datetime.datetime | None = typer.Option(None, "--purchased-at"),
    provider_updated_at: datetime.datetime | None = typer.Option(None, "--provider-updated-at"),
    source_transaction_id: uuid.UUID | None = typer.Option(None, "--source-transaction-id"),
    actor_id: str = typer.Option(str(DEFAULT_ADMIN_ACTOR_ID), "--actor-id"),
    parameters: list[str] | None = typer.Option(None, "--parameter"),
    one_time_purchase_id: uuid.UUID | None = typer.Option(None, "--one-time-purchase-id"),
) -> None:
    operation_time = core_utils.now()

    try:
        normalized_status = purchase_status_from_name(
            option_or_creation_default(
                status,
                target_id=one_time_purchase_id,
                option_name="--status",
                creation_default="completed",
            )
        )
        snapshot = PurchaseSnapshot(
            user_id=UserId(user_id),
            benefit_id=BenefitId(benefit_id),
            status=normalized_status,
            provider_status=ProviderStatus(
                option_or_creation_default(
                    provider_status,
                    target_id=one_time_purchase_id,
                    option_name="--provider-status",
                    creation_default=normalized_status.name,
                )
            ),
            purchased_at=option_or_creation_default(
                purchased_at,
                target_id=one_time_purchase_id,
                option_name="--purchased-at",
                creation_default=operation_time,
            ),
            provider_updated_at=option_or_creation_default(
                provider_updated_at,
                target_id=one_time_purchase_id,
                option_name="--provider-updated-at",
                creation_default=operation_time,
            ),
        )
        normalized_parameters = benefit_parameters_from_options(parameters or [])
        transaction = BenefitTransactionCommand[OneTimePurchaseId](
            source_id=ADMIN_BENEFIT_SOURCE_ID,
            source_transaction_id=BenefitSourceTransactionId(source_transaction_id or uuid.uuid4()),
            target=(
                InternalTarget(internal_id=OneTimePurchaseId(one_time_purchase_id))
                if one_time_purchase_id is not None
                else NewTarget()
            ),
            effective_at=operation_time,
        )
        normalized_actor_id = pydantic.TypeAdapter(SerializedId).validate_python(actor_id)
    except pydantic.ValidationError as error:
        raise typer.BadParameter("invalid one-time-purchase benefit parameters") from error

    run_async_command(run_apply_one_time_purchase(snapshot, normalized_parameters, transaction, normalized_actor_id))
