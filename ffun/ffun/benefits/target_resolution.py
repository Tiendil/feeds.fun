from functools import singledispatch

from ffun.benefits.entities import (
    ExternalTarget,
    InternalTarget,
    NewTarget,
)
from ffun.core.postgresql import ExecuteType
from ffun.domain.entities import OneTimePurchaseId, SubscriptionId
from ffun.one_time_purchases import domain as purchase_domain
from ffun.subscriptions import domain as subscription_domain


@singledispatch  # type: ignore[misc]
async def resolve_subscription_target(
    target: object,
    execute: ExecuteType,
) -> SubscriptionId:
    raise NotImplementedError(f"Unsupported subscription target: {target!r}")


@resolve_subscription_target.register(InternalTarget)
async def _resolve_internal_subscription_target(
    target: InternalTarget[SubscriptionId],
    _execute: ExecuteType,
) -> SubscriptionId:
    return target.internal_id


@resolve_subscription_target.register  # type: ignore[misc]
async def _resolve_external_subscription_target(
    target: ExternalTarget,
    execute: ExecuteType,
) -> SubscriptionId:
    return await subscription_domain.resolve_provider_subscription_reference(
        execute,
        target.provider_reference,
    )


@resolve_subscription_target.register  # type: ignore[misc]
async def _resolve_new_subscription_target(
    _target: NewTarget,
    _execute: ExecuteType,
) -> SubscriptionId:
    return subscription_domain.new_subscription_id()


@singledispatch  # type: ignore[misc]
async def resolve_one_time_purchase_target(
    target: object,
    execute: ExecuteType,
) -> OneTimePurchaseId:
    raise NotImplementedError(f"Unsupported one-time purchase target: {target!r}")


@resolve_one_time_purchase_target.register(InternalTarget)
async def _resolve_internal_one_time_purchase_target(
    target: InternalTarget[OneTimePurchaseId],
    _execute: ExecuteType,
) -> OneTimePurchaseId:
    return target.internal_id


@resolve_one_time_purchase_target.register  # type: ignore[misc]
async def _resolve_external_one_time_purchase_target(
    target: ExternalTarget,
    execute: ExecuteType,
) -> OneTimePurchaseId:
    return await purchase_domain.resolve_provider_purchase_reference(
        execute,
        target.provider_reference,
    )


@resolve_one_time_purchase_target.register  # type: ignore[misc]
async def _resolve_new_one_time_purchase_target(
    _target: NewTarget,
    _execute: ExecuteType,
) -> OneTimePurchaseId:
    return purchase_domain.new_purchase_id()
