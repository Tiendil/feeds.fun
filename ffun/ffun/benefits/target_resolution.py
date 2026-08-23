from functools import singledispatch

from ffun.benefits.entities import (
    ExternalTarget,
    InternalTarget,
    NewTarget,
    OneTimePurchaseTarget,
    SubscriptionTarget,
)
from ffun.core.postgresql import ExecuteType
from ffun.domain.entities import OneTimePurchaseId, SubscriptionId
from ffun.one_time_purchases import domain as purchase_domain
from ffun.subscriptions import domain as subscription_domain


@singledispatch  # type: ignore[misc]
async def _load_subscription_target(
    target: object,
    execute: ExecuteType,
) -> SubscriptionId | None:
    raise NotImplementedError(f"Unsupported subscription target: {target!r}")


@_load_subscription_target.register(InternalTarget)
async def _load_internal_subscription_target(
    target: InternalTarget[SubscriptionId],
    _execute: ExecuteType,
) -> SubscriptionId:
    return target.internal_id


@_load_subscription_target.register  # type: ignore[misc]
async def _load_external_subscription_target(
    target: ExternalTarget,
    execute: ExecuteType,
) -> SubscriptionId | None:
    return await subscription_domain.load_provider_subscription_reference(
        execute,
        target.provider_reference,
    )


@_load_subscription_target.register  # type: ignore[misc]
async def _load_new_subscription_target(
    _target: NewTarget,
    _execute: ExecuteType,
) -> None:
    return None


async def resolve_subscription_target(
    execute: ExecuteType,
    target: SubscriptionTarget,
) -> SubscriptionId:
    subscription_id = await _load_subscription_target(target, execute)

    if subscription_id is None:
        subscription_id = subscription_domain.new_subscription_id()

    if target.provider_reference is not None:
        await subscription_domain.insert_provider_subscription_reference(
            execute,
            target.provider_reference,
            subscription_id=subscription_id,
        )

    return subscription_id


@singledispatch  # type: ignore[misc]
async def _load_one_time_purchase_target(
    target: object,
    execute: ExecuteType,
) -> OneTimePurchaseId | None:
    raise NotImplementedError(f"Unsupported one-time purchase target: {target!r}")


@_load_one_time_purchase_target.register(InternalTarget)
async def _load_internal_one_time_purchase_target(
    target: InternalTarget[OneTimePurchaseId],
    _execute: ExecuteType,
) -> OneTimePurchaseId:
    return target.internal_id


@_load_one_time_purchase_target.register  # type: ignore[misc]
async def _load_external_one_time_purchase_target(
    target: ExternalTarget,
    execute: ExecuteType,
) -> OneTimePurchaseId | None:
    return await purchase_domain.load_provider_purchase_reference(
        execute,
        target.provider_reference,
    )


@_load_one_time_purchase_target.register  # type: ignore[misc]
async def _load_new_one_time_purchase_target(
    _target: NewTarget,
    _execute: ExecuteType,
) -> None:
    return None


async def resolve_one_time_purchase_target(
    execute: ExecuteType,
    target: OneTimePurchaseTarget,
) -> OneTimePurchaseId:
    one_time_purchase_id = await _load_one_time_purchase_target(target, execute)

    if one_time_purchase_id is None:
        one_time_purchase_id = purchase_domain.new_purchase_id()

    if target.provider_reference is not None:
        await purchase_domain.insert_provider_purchase_reference(
            execute,
            target.provider_reference,
            one_time_purchase_id=one_time_purchase_id,
        )

    return one_time_purchase_id
