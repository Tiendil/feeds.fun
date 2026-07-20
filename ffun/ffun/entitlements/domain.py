import datetime
import dataclasses
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
    MergePolicy,
    SourceEntitlement,
)
from ffun.locks.domain import locked_transaction
from ffun.locks.entities import LockKind

logger = logging.get_module_logger()


@dataclasses.dataclass(frozen=True, slots=True)
class _SourceChangeOutcome:
    changed: bool
    effective_state: EffectiveEntitlementState
    effective_intervals: list[EffectiveEntitlementInterval]


def get_entitlement_kind(kind_id: EntitlementKindId) -> EntitlementKind:
    for kind in entitlement_entities.ENTITLEMENT_KINDS:
        if kind.id == kind_id:
            return kind

    raise errors.UnknownEntitlementKind(kind_id=kind_id)


def validate_source_change(  # noqa: CFQ002, CCR001
    *,
    source: EntitlementSourceId,
    kind_id: EntitlementKindId,
    granted: bool,
    value: int | None,
    starts_at: datetime.datetime,
    expires_at: datetime.datetime,
    actor_id: SerializedId,
) -> EntitlementKind:
    kind = get_entitlement_kind(kind_id)

    if not source:
        raise errors.InvalidSourceEntitlement(reason="Entitlement source must not be empty")

    if granted and value is None:
        raise errors.InvalidSourceEntitlement(reason="A granted entitlement must have an integer value")

    if not granted and value is not None:
        raise errors.InvalidSourceEntitlement(reason="A revoked entitlement must not have a value")

    if starts_at.tzinfo is None or starts_at.utcoffset() is None:
        raise errors.InvalidSourceEntitlement(reason="Entitlement activation timestamp must have a UTC offset")

    if expires_at.tzinfo is None or expires_at.utcoffset() is None:
        raise errors.InvalidSourceEntitlement(reason="Entitlement expiration timestamp must have a UTC offset")

    if starts_at >= expires_at:
        raise errors.InvalidSourceEntitlement(
            reason="Entitlement activation timestamp must be earlier than expiration"
        )

    if not actor_id or not actor_id.strip():
        raise errors.InvalidActorId(reason="Audit actor id must not be empty")

    return kind


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
    granted_entitlements = [entitlement for entitlement in source_entitlements if entitlement.granted]
    boundaries = sorted(
        {
            boundary
            for entitlement in granted_entitlements
            for boundary in (entitlement.starts_at, entitlement.expires_at)
        }
    )
    intervals: list[EffectiveEntitlementInterval] = []

    for starts_at, expires_at in itertools.pairwise(boundaries):
        if expires_at <= evaluation_time:
            continue

        values = [
            entitlement.value
            for entitlement in granted_entitlements
            if entitlement.starts_at <= starts_at and expires_at <= entitlement.expires_at
        ]
        merged_value = merge_values(merge_policy, [value for value in values if value is not None]) if values else None

        if merged_value is None:
            continue

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


async def _apply_source_change(
    execute: ExecuteType,
    *,
    kind: EntitlementKind,
    new_source_state: SourceEntitlement,
    evaluation_time: datetime.datetime,
    actor_kind: AuditEntityKind,
    actor_id: SerializedId,
) -> _SourceChangeOutcome:
    previous_source_state = await operations.load_source_entitlement(
        execute,
        new_source_state.user_id,
        new_source_state.kind_id,
        new_source_state.source,
    )
    previous_effective_intervals = await operations.load_effective_intervals(
        execute,
        new_source_state.user_id,
        new_source_state.kind_id,
        ending_after=evaluation_time,
    )

    if previous_source_state == new_source_state:
        return _SourceChangeOutcome(
            changed=False,
            effective_state=effective_state_at(previous_effective_intervals, evaluation_time),
            effective_intervals=previous_effective_intervals,
        )

    await operations.upsert_source_entitlement(execute, new_source_state)
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
    )


def _emit_business_events(source_state: SourceEntitlement, outcome: _SourceChangeOutcome) -> None:
    logger.business_event(
        "source_entitlement_changed",
        user_id=source_state.user_id,
        source=source_state.source,
        kind_id=source_state.kind_id,
        granted=source_state.granted,
        value=source_state.value,
        starts_at=source_state.starts_at.isoformat(),
        expires_at=source_state.expires_at.isoformat(),
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
) -> EffectiveEntitlementState:
    kind = validate_source_change(
        source=source,
        kind_id=kind_id,
        granted=granted,
        value=value,
        starts_at=starts_at,
        expires_at=expires_at,
        actor_id=actor_id,
    )
    evaluation_time = datetime.datetime.now(tz=datetime.UTC)
    new_source_state = SourceEntitlement(
        source=source,
        user_id=user_id,
        kind_id=kind_id,
        granted=granted,
        value=value,
        starts_at=starts_at,
        expires_at=expires_at,
    )

    async with locked_transaction(LockKind("entitlements_user_kind"), user_id, kind_id) as transaction_execute:
        outcome = await _apply_source_change(
            transaction_execute,
            kind=kind,
            new_source_state=new_source_state,
            evaluation_time=evaluation_time,
            actor_kind=actor_kind,
            actor_id=actor_id,
        )

    if outcome.changed:
        _emit_business_events(new_source_state, outcome)

    return outcome.effective_state


async def get_entitlements(
    user_ids: list[UserId], kind_ids: list[EntitlementKindId]
) -> Mapping[UserId, Mapping[EntitlementKindId, bool]]:
    selected_user_ids = list({user_id: None for user_id in user_ids})
    selected_kind_ids = (
        list({kind_id: None for kind_id in kind_ids})
        if kind_ids
        else [kind.id for kind in entitlement_entities.ENTITLEMENT_KINDS]
    )

    for kind_id in selected_kind_ids:
        get_entitlement_kind(kind_id)

    result: dict[UserId, dict[EntitlementKindId, bool]] = {
        user_id: {kind_id: False for kind_id in selected_kind_ids} for user_id in selected_user_ids
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
        result[interval.user_id][interval.kind_id] = True

    return result


async def cleanup_expired_entitlements() -> int:
    cleanup_time = datetime.datetime.now(tz=datetime.UTC)
    return await operations.delete_expired_effective_intervals(execute, cleanup_time)
