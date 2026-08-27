import datetime
import itertools
from collections.abc import Callable, Mapping, Sequence
from functools import partial
from typing import assert_never, cast

from ffun.audit import domain as audit_domain
from ffun.audit.entities import AuditEntityKind, AuditEventName
from ffun.core import logging
from ffun.core.postgresql import ExecuteType, TransactionExecuteType, execute
from ffun.domain.entities import BenefitTransactionId, OneTimePurchaseId, SerializedId, SubscriptionId, UserId
from ffun.entitlements import entities as entitlement_entities
from ffun.entitlements import errors, operations
from ffun.entitlements.entities import (
    EffectiveEntitlementInterval,
    EffectiveEntitlementState,
    EntitlementGuarantee,
    EntitlementKind,
    EntitlementKindId,
    EntitlementSourceId,
    MergePolicy,
    SourceEntitlement,
    SourceEntitlementChange,
)
from ffun.locks.domain import Lock
from ffun.locks.entities import LockKind

logger = logging.get_module_logger()

load_source_entitlements_for_subscription = operations.load_source_entitlements_for_subscription


def _empty_business_event_callback() -> None:
    pass


def get_entitlement_kind(kind_id: EntitlementKindId) -> EntitlementKind:
    for kind in entitlement_entities.ENTITLEMENT_KINDS:
        if kind.id == kind_id:
            return kind

    raise errors.UnknownEntitlementKind(kind_id=kind_id)


def _guarantee_kind_id(guarantee: EntitlementGuarantee) -> EntitlementKindId:
    return guarantee.kind_id


def merge_values(policy: MergePolicy, values: Sequence[int]) -> int:
    if not values:
        raise errors.InvalidMergeValues(reason="At least one entitlement value is required for merging")

    match policy:
        case MergePolicy.max:
            value = max(values)
        case MergePolicy.min:
            value = min(values)
        case MergePolicy.sum:
            value = sum(values)
        case _:
            assert_never(policy)

    if not entitlement_entities.MIN_ENTITLEMENT_VALUE <= value <= entitlement_entities.MAX_ENTITLEMENT_VALUE:
        raise errors.InvalidMergeValues(reason="Merged entitlement value exceeds persistence-safe bounds")

    return value


def build_effective_timeline(  # noqa: CCR001
    *,
    user_id: UserId,
    kind_id: EntitlementKindId,
    merge_policy: MergePolicy,
    source_entitlements: Sequence[SourceEntitlement],
    evaluation_time: datetime.datetime,
) -> list[EffectiveEntitlementInterval]:
    unrevoked_source_entitlements = [
        entitlement for entitlement in source_entitlements if entitlement.revoked_at is None
    ]
    boundaries = sorted(
        {
            boundary
            for entitlement in unrevoked_source_entitlements
            for boundary in (entitlement.starts_at, entitlement.expires_at)
        }
    )
    intervals: list[EffectiveEntitlementInterval] = []

    for starts_at, expires_at in itertools.pairwise(boundaries):
        if expires_at <= evaluation_time:
            continue

        values = [
            entitlement.value
            for entitlement in unrevoked_source_entitlements
            if entitlement.starts_at <= starts_at and expires_at <= entitlement.expires_at
        ]

        if not values:
            continue

        merged_value = merge_values(merge_policy, values)

        if intervals and intervals[-1].value == merged_value and intervals[-1].expires_at == starts_at:
            intervals[-1] = intervals[-1].replace(expires_at=expires_at)
            continue

        intervals.append(
            EffectiveEntitlementInterval(
                user_id=user_id,
                kind_id=kind_id,
                value=merged_value,
                starts_at=starts_at,
                expires_at=expires_at,
            )
        )

    return intervals


def effective_state_at(
    intervals: Sequence[EffectiveEntitlementInterval], evaluation_time: datetime.datetime
) -> EffectiveEntitlementState:
    for interval in intervals:
        if interval.starts_at <= evaluation_time < interval.expires_at:
            return (True, interval.value)

    return (False, None)


async def _rebuild_after_source_change(  # noqa: CFQ002
    execute: ExecuteType,
    *,
    kind: EntitlementKind,
    previous_source_state: SourceEntitlement | None,
    new_source_state: SourceEntitlement,
    previous_effective_intervals: list[EffectiveEntitlementInterval],
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> SourceEntitlementChange:
    source_entitlements = await operations.load_source_entitlements(
        execute,
        new_source_state.user_id,
        new_source_state.kind_id,
    )
    new_effective_intervals = build_effective_timeline(
        user_id=new_source_state.user_id,
        kind_id=new_source_state.kind_id,
        merge_policy=kind.merge_policy,
        source_entitlements=source_entitlements,
        evaluation_time=evaluation_time,
    )
    await operations.replace_effective_intervals(
        execute,
        new_source_state.user_id,
        new_source_state.kind_id,
        new_effective_intervals,
    )
    effective_state = effective_state_at(new_effective_intervals, evaluation_time)
    await audit_domain.record(
        execute,
        event=AuditEventName("source_entitlement_changed"),
        actor_kind=actor_kind,
        actor_id=actor_id,
        subject_kind=AuditEntityKind.user,
        subject_id=SerializedId(str(new_source_state.user_id)),
        attributes={
            "source_id": new_source_state.source_id,
            "subscription_id": (
                str(new_source_state.subscription_id) if new_source_state.subscription_id is not None else None
            ),
            "one_time_purchase_id": (
                str(new_source_state.one_time_purchase_id)
                if new_source_state.one_time_purchase_id is not None
                else None
            ),
            "grant_transaction_id": str(new_source_state.grant_transaction_id),
            "revoked_by_transaction_id": (
                str(new_source_state.revoked_by_transaction_id)
                if new_source_state.revoked_by_transaction_id is not None
                else None
            ),
            "kind_id": new_source_state.kind_id,
            "previous_source_state": (
                cast(dict[str, object], previous_source_state.model_dump(mode="json"))
                if previous_source_state is not None
                else None
            ),
            "new_source_state": cast(dict[str, object], new_source_state.model_dump(mode="json")),
            "previous_effective_intervals": [
                cast(dict[str, object], interval.model_dump(mode="json")) for interval in previous_effective_intervals
            ],
            "new_effective_intervals": [
                cast(dict[str, object], interval.model_dump(mode="json")) for interval in new_effective_intervals
            ],
        },
    )

    return SourceEntitlementChange(
        changed=True,
        effective_state=effective_state,
        effective_intervals=new_effective_intervals,
        source_state=new_source_state,
    )


def _unchanged_outcome(
    source_state: SourceEntitlement,
    effective_intervals: list[EffectiveEntitlementInterval],
    evaluation_time: datetime.datetime,
) -> SourceEntitlementChange:
    return SourceEntitlementChange(
        changed=False,
        effective_state=effective_state_at(effective_intervals, evaluation_time),
        effective_intervals=effective_intervals,
        source_state=source_state,
    )


async def _apply_source_grant(
    execute: ExecuteType,
    *,
    kind: EntitlementKind,
    source_state: SourceEntitlement,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> SourceEntitlementChange:
    previous_source_state = await operations.load_source_entitlement(
        execute,
        source_state.user_id,
        source_state.kind_id,
        source_state.source_id,
        source_state.grant_transaction_id,
    )
    previous_effective_intervals = await operations.load_effective_intervals(
        execute,
        source_state.user_id,
        source_state.kind_id,
        ending_after=evaluation_time,
    )

    if previous_source_state is not None:
        if previous_source_state.has_same_grant_as(source_state):
            return _unchanged_outcome(previous_source_state, previous_effective_intervals, evaluation_time)

        raise errors.SourceEntitlementConflict(
            user_id=str(source_state.user_id),
            kind_id=source_state.kind_id,
            source_id=source_state.source_id,
            grant_transaction_id=str(source_state.grant_transaction_id),
        )

    await operations.insert_source_entitlement(execute, source_state)
    return await _rebuild_after_source_change(
        execute,
        kind=kind,
        previous_source_state=None,
        new_source_state=source_state,
        previous_effective_intervals=previous_effective_intervals,
        evaluation_time=evaluation_time,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )


async def _apply_source_revocation(  # noqa: CFQ002
    execute: ExecuteType,
    *,
    kind: EntitlementKind,
    source_id: EntitlementSourceId,
    grant_transaction_id: BenefitTransactionId,
    revoked_by_transaction_id: BenefitTransactionId,
    user_id: UserId,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> SourceEntitlementChange:
    previous_source_state = await operations.load_source_entitlement(
        execute,
        user_id,
        kind.id,
        source_id,
        grant_transaction_id,
    )

    previous_effective_intervals = await operations.load_effective_intervals(
        execute,
        user_id,
        kind.id,
        ending_after=evaluation_time,
    )

    if previous_source_state is None:
        raise errors.SourceEntitlementNotFound(
            user_id=str(user_id),
            kind_id=kind.id,
            source_id=source_id,
            grant_transaction_id=str(grant_transaction_id),
        )

    if previous_source_state.revoked_at is not None:
        return _unchanged_outcome(previous_source_state, previous_effective_intervals, evaluation_time)

    new_source_state = await operations.revoke_source_entitlement(
        execute,
        previous_source_state,
        revoked_at=evaluation_time,
        revoked_by_transaction_id=revoked_by_transaction_id,
    )
    return await _rebuild_after_source_change(
        execute,
        kind=kind,
        previous_source_state=previous_source_state,
        new_source_state=new_source_state,
        previous_effective_intervals=previous_effective_intervals,
        evaluation_time=evaluation_time,
        actor_kind=actor_kind,
        actor_id=actor_id,
    )


def _emit_source_change_events(outcome: SourceEntitlementChange) -> None:
    source_state = outcome.source_state
    logger.business_event(
        "source_entitlement_changed",
        user_id=source_state.user_id,
        source_id=source_state.source_id,
        subscription_id=source_state.subscription_id,
        one_time_purchase_id=source_state.one_time_purchase_id,
        grant_transaction_id=source_state.grant_transaction_id,
        kind_id=source_state.kind_id,
        granted=source_state.granted,
        value=source_state.value,
        starts_at=source_state.starts_at.isoformat(),
        expires_at=source_state.expires_at.isoformat(),
        revoked_at=source_state.revoked_at.isoformat() if source_state.revoked_at is not None else None,
        revoked_by_transaction_id=source_state.revoked_by_transaction_id,
    )
    logger.business_event(
        "entitlement_changed",
        user_id=source_state.user_id,
        kind_id=source_state.kind_id,
        granted=outcome.effective_state[0],
        value=outcome.effective_state[1],
        new_effective_intervals=[
            {
                "value": interval.value,
                "starts_at": interval.starts_at.isoformat(),
                "expires_at": interval.expires_at.isoformat(),
            }
            for interval in outcome.effective_intervals
        ],
    )


async def grant_source_entitlement(
    execute: TransactionExecuteType,
    source_entitlement: SourceEntitlement,
    *,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> tuple[SourceEntitlementChange, Callable[[], None]]:
    kind = get_entitlement_kind(source_entitlement.kind_id)

    try:
        source_entitlement.validate_grant(kind)
    except ValueError as error:
        raise errors.InvalidSourceEntitlement(reason=str(error)) from error

    async with Lock(
        execute, LockKind("entitlements_user_kind"), source_entitlement.user_id, source_entitlement.kind_id
    ):
        outcome = await _apply_source_grant(
            execute,
            kind=kind,
            source_state=source_entitlement,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        )

    event_callback: Callable[[], None]

    if outcome.changed:
        event_callback = partial(_emit_source_change_events, outcome)
    else:
        event_callback = _empty_business_event_callback

    return outcome, event_callback


async def revoke_source_entitlement(  # noqa: CFQ002
    execute: TransactionExecuteType,
    *,
    source_id: EntitlementSourceId,
    grant_transaction_id: BenefitTransactionId,
    revoked_by_transaction_id: BenefitTransactionId,
    user_id: UserId,
    kind_id: EntitlementKindId,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> tuple[SourceEntitlementChange, Callable[[], None]]:
    kind = get_entitlement_kind(kind_id)

    async with Lock(execute, LockKind("entitlements_user_kind"), user_id, kind_id):
        outcome = await _apply_source_revocation(
            execute,
            kind=kind,
            source_id=source_id,
            grant_transaction_id=grant_transaction_id,
            revoked_by_transaction_id=revoked_by_transaction_id,
            user_id=user_id,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        )

    event_callback: Callable[[], None]

    if outcome.changed:
        event_callback = partial(_emit_source_change_events, outcome)
    else:
        event_callback = _empty_business_event_callback

    return outcome, event_callback


async def grant_source_entitlements(  # noqa: CFQ002
    execute: TransactionExecuteType,
    *,
    source_id: EntitlementSourceId,
    grant_transaction_id: BenefitTransactionId,
    user_id: UserId,
    subscription_id: SubscriptionId | None,
    one_time_purchase_id: OneTimePurchaseId | None,
    guarantees: Sequence[EntitlementGuarantee],
    starts_at: datetime.datetime,
    expires_at: datetime.datetime,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> tuple[list[SourceEntitlementChange], list[Callable[[], None]]]:
    outcomes: list[SourceEntitlementChange] = []
    event_callbacks: list[Callable[[], None]] = []

    for guarantee in sorted(guarantees, key=_guarantee_kind_id):
        try:
            entitlement = SourceEntitlement(
                source_id=source_id,
                grant_transaction_id=grant_transaction_id,
                user_id=user_id,
                subscription_id=subscription_id,
                one_time_purchase_id=one_time_purchase_id,
                kind_id=guarantee.kind_id,
                value=guarantee.value,
                starts_at=starts_at,
                expires_at=expires_at,
            )
        except ValueError as error:
            raise errors.InvalidSourceEntitlement(reason=str(error)) from error

        outcome, callback = await grant_source_entitlement(
            execute,
            entitlement,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        )
        outcomes.append(outcome)
        event_callbacks.append(callback)

    return outcomes, event_callbacks


async def revoke_subscription_entitlements(  # noqa: CFQ002
    execute: TransactionExecuteType,
    *,
    subscription_id: SubscriptionId,
    revoked_by_transaction_id: BenefitTransactionId,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> tuple[list[SourceEntitlementChange], list[Callable[[], None]]]:
    source_entitlements = [
        entitlement
        for entitlement in await operations.load_source_entitlements_for_subscription(execute, subscription_id)
        if entitlement.revoked_at is None
    ]
    outcomes: list[SourceEntitlementChange] = []
    event_callbacks: list[Callable[[], None]] = []

    for source_entitlement in source_entitlements:
        outcome, callback = await revoke_source_entitlement(
            execute,
            source_id=source_entitlement.source_id,
            grant_transaction_id=source_entitlement.grant_transaction_id,
            revoked_by_transaction_id=revoked_by_transaction_id,
            user_id=source_entitlement.user_id,
            kind_id=source_entitlement.kind_id,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        )
        outcomes.append(outcome)
        event_callbacks.append(callback)

    return outcomes, event_callbacks


async def revoke_one_time_purchase_entitlements(  # noqa: CFQ002
    execute: TransactionExecuteType,
    *,
    one_time_purchase_id: OneTimePurchaseId,
    revoked_by_transaction_id: BenefitTransactionId,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> tuple[list[SourceEntitlementChange], list[Callable[[], None]]]:
    source_entitlements = [
        entitlement
        for entitlement in await operations.load_source_entitlements_for_one_time_purchase(
            execute, one_time_purchase_id
        )
        if entitlement.revoked_at is None
    ]
    outcomes: list[SourceEntitlementChange] = []
    event_callbacks: list[Callable[[], None]] = []

    for source_entitlement in source_entitlements:
        outcome, callback = await revoke_source_entitlement(
            execute,
            source_id=source_entitlement.source_id,
            grant_transaction_id=source_entitlement.grant_transaction_id,
            revoked_by_transaction_id=revoked_by_transaction_id,
            user_id=source_entitlement.user_id,
            kind_id=source_entitlement.kind_id,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        )
        outcomes.append(outcome)
        event_callbacks.append(callback)

    return outcomes, event_callbacks


async def get_entitlements(
    user_ids: list[UserId], kind_ids: list[EntitlementKindId]
) -> Mapping[UserId, Mapping[EntitlementKindId, EffectiveEntitlementInterval | None]]:
    selected_user_ids = list({user_id: None for user_id in user_ids})
    selected_kind_ids = (
        list({kind_id: None for kind_id in kind_ids})
        if kind_ids
        else [kind.id for kind in entitlement_entities.ENTITLEMENT_KINDS]
    )

    for kind_id in selected_kind_ids:
        get_entitlement_kind(kind_id)

    result: dict[UserId, dict[EntitlementKindId, EffectiveEntitlementInterval | None]] = {
        user_id: {kind_id: None for kind_id in selected_kind_ids} for user_id in selected_user_ids
    }

    if not selected_user_ids or not selected_kind_ids:
        return result

    evaluation_time = datetime.datetime.now(tz=datetime.UTC)
    active_intervals = await operations.load_active_intervals(
        execute,
        selected_user_ids,
        selected_kind_ids,
        evaluation_time=evaluation_time,
    )

    for interval in active_intervals:
        result[interval.user_id][interval.kind_id] = interval

    return result


async def cleanup_expired_entitlements() -> int:
    cleanup_time = datetime.datetime.now(tz=datetime.UTC)
    return await operations.delete_expired_effective_intervals(execute, cleanup_time)
