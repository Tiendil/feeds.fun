import datetime
import itertools
from collections.abc import Mapping, Sequence
from typing import cast

from ffun.audit import domain as audit_domain
from ffun.audit.entities import AuditEntityKind, AuditEventName
from ffun.core import logging
from ffun.core.postgresql import ExecuteType, execute
from ffun.domain.entities import SerializedId, UserId
from ffun.entitlements import entities as entitlement_entities
from ffun.entitlements import errors, operations
from ffun.entitlements.entities import (
    EffectiveEntitlementInterval,
    EffectiveEntitlementState,
    EntitlementKind,
    EntitlementKindId,
    EntitlementSourceId,
    EntitlementTransactionId,
    MergePolicy,
    SourceEntitlement,
)
from ffun.locks.domain import locked_transaction
from ffun.locks.entities import LockKind

logger = logging.get_module_logger()


class _SourceChangeOutcome:
    __slots__ = ("changed", "effective_state", "effective_intervals", "source_state")

    def __init__(
        self,
        *,
        changed: bool,
        effective_state: EffectiveEntitlementState,
        effective_intervals: list[EffectiveEntitlementInterval],
        source_state: SourceEntitlement,
    ) -> None:
        self.changed = changed
        self.effective_state = effective_state
        self.effective_intervals = effective_intervals
        self.source_state = source_state


def get_entitlement_kind(kind_id: EntitlementKindId) -> EntitlementKind:
    for kind in entitlement_entities.ENTITLEMENT_KINDS:
        if kind.id == kind_id:
            return kind

    raise errors.UnknownEntitlementKind(kind_id=kind_id)


def merge_values(policy: MergePolicy, values: Sequence[int]) -> int:
    if not values:
        raise errors.InvalidMergeValues(reason="At least one entitlement value is required for merging")

    if policy == MergePolicy.max:
        return max(values)

    if policy == MergePolicy.min:
        return min(values)

    if policy == MergePolicy.sum:
        return sum(values)

    raise AssertionError(f"Unsupported entitlement merge policy: {policy}")


def build_effective_timeline(  # noqa: CCR001
    *,
    user_id: UserId,
    kind_id: EntitlementKindId,
    merge_policy: MergePolicy,
    source_entitlements: Sequence[SourceEntitlement],
    evaluation_time: datetime.datetime,
) -> list[EffectiveEntitlementInterval]:
    boundaries = sorted(
        {
            boundary
            for entitlement in source_entitlements
            for boundary in (entitlement.starts_at, entitlement.expires_at, entitlement.revoked_at)
            if boundary is not None
        }
    )
    intervals: list[EffectiveEntitlementInterval] = []

    for starts_at, expires_at in itertools.pairwise(boundaries):
        if expires_at <= evaluation_time:
            continue

        values = [
            entitlement.value
            for entitlement in source_entitlements
            if entitlement.starts_at <= starts_at
            and expires_at <= entitlement.expires_at
            and (entitlement.revoked_at is None or expires_at <= entitlement.revoked_at)
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
) -> _SourceChangeOutcome:
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
            "source": new_source_state.source,
            "transaction_id": new_source_state.transaction_id,
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

    return _SourceChangeOutcome(
        changed=True,
        effective_state=effective_state,
        effective_intervals=new_effective_intervals,
        source_state=new_source_state,
    )


def _unchanged_outcome(
    source_state: SourceEntitlement,
    effective_intervals: list[EffectiveEntitlementInterval],
    evaluation_time: datetime.datetime,
) -> _SourceChangeOutcome:
    return _SourceChangeOutcome(
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
) -> _SourceChangeOutcome:
    previous_source_state = await operations.load_source_entitlement(
        execute,
        source_state.user_id,
        source_state.kind_id,
        source_state.source,
        source_state.transaction_id,
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
            source=source_state.source,
            transaction_id=source_state.transaction_id,
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
    source: EntitlementSourceId,
    transaction_id: EntitlementTransactionId,
    user_id: UserId,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> _SourceChangeOutcome:
    previous_source_state = await operations.load_source_entitlement(
        execute,
        user_id,
        kind.id,
        source,
        transaction_id,
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
            source=source,
            transaction_id=transaction_id,
        )

    if previous_source_state.revoked_at is not None:
        return _unchanged_outcome(previous_source_state, previous_effective_intervals, evaluation_time)

    new_source_state = previous_source_state.to_revoked(revoked_at=evaluation_time)
    await operations.revoke_source_entitlement(execute, previous_source_state, revoked_at=evaluation_time)
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


def _emit_business_events(outcome: _SourceChangeOutcome) -> None:
    source_state = outcome.source_state
    logger.business_event(
        "source_entitlement_changed",
        user_id=source_state.user_id,
        source=source_state.source,
        transaction_id=source_state.transaction_id,
        kind_id=source_state.kind_id,
        granted=source_state.granted,
        value=source_state.value,
        starts_at=source_state.starts_at.isoformat(),
        expires_at=source_state.expires_at.isoformat(),
        revoked_at=source_state.revoked_at.isoformat() if source_state.revoked_at is not None else None,
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
    source_entitlement: SourceEntitlement,
    *,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> EffectiveEntitlementState:
    kind = get_entitlement_kind(source_entitlement.kind_id)

    try:
        source_entitlement.validate_grant(kind)
    except ValueError as error:
        raise errors.InvalidSourceEntitlement(reason=str(error)) from error

    evaluation_time = datetime.datetime.now(tz=datetime.UTC)

    async with locked_transaction(
        LockKind("entitlements_user_kind"), source_entitlement.user_id, source_entitlement.kind_id
    ) as transaction_execute:
        outcome = await _apply_source_grant(
            transaction_execute,
            kind=kind,
            source_state=source_entitlement,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        )

    if outcome.changed:
        _emit_business_events(outcome)

    return outcome.effective_state


async def revoke_source_entitlement(
    *,
    source: EntitlementSourceId,
    transaction_id: EntitlementTransactionId,
    user_id: UserId,
    kind_id: EntitlementKindId,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> EffectiveEntitlementState:
    kind = get_entitlement_kind(kind_id)
    evaluation_time = datetime.datetime.now(tz=datetime.UTC)

    async with locked_transaction(LockKind("entitlements_user_kind"), user_id, kind_id) as transaction_execute:
        outcome = await _apply_source_revocation(
            transaction_execute,
            kind=kind,
            source=source,
            transaction_id=transaction_id,
            user_id=user_id,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        )

    if outcome.changed:
        _emit_business_events(outcome)

    return outcome.effective_state


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
