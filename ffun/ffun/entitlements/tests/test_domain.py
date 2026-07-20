import datetime
from typing import cast

import pytest
from pytest_mock import MockerFixture

from ffun.audit import domain as audit_domain
from ffun.audit.entities import AuditEntityKind
from ffun.core.postgresql import execute, transaction
from ffun.core.tests.helpers import (
    TableSizeDelta,
    TableSizeNotChanged,
    assert_logs_has_business_event,
    assert_logs_has_no_business_event,
    capture_logs,
)
from ffun.domain.domain import new_user_id
from ffun.domain.entities import SerializedId
from ffun.entitlements import domain
from ffun.entitlements import entities as entitlement_entities
from ffun.entitlements import errors, operations
from ffun.entitlements.entities import EntitlementKindId, EntitlementSourceId, MergePolicy
from ffun.entitlements.tests.helpers import clear_effective_intervals
from ffun.entitlements.tests.make import make_effective_entitlement_interval, make_source_entitlement

_DAY_TOKENS = EntitlementKindId.day_tokens
_MONTH_TOKENS = EntitlementKindId.month_tokens
_SOURCE = EntitlementSourceId("test")
_ACTOR_KIND = AuditEntityKind.admin
_ACTOR_ID = SerializedId("test-admin")


class TestGetEntitlementKind:
    def test_known_kind(self) -> None:
        kind = domain.get_entitlement_kind(_DAY_TOKENS)

        assert kind.id == _DAY_TOKENS
        assert kind.merge_policy == MergePolicy.max

    def test_unconfigured_kind(self, mocker: MockerFixture) -> None:
        mocker.patch.object(
            entitlement_entities,
            "ENTITLEMENT_KINDS",
            (entitlement_entities.ENTITLEMENT_KINDS[0],),
        )

        with pytest.raises(errors.UnknownEntitlementKind):
            domain.get_entitlement_kind(_MONTH_TOKENS)


class TestValidateSourceChange:
    def test_valid(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        kind = domain.validate_source_change(
            source=EntitlementSourceId("test"),
            kind_id=_DAY_TOKENS,
            granted=True,
            value=10,
            starts_at=now,
            expires_at=now + datetime.timedelta(days=1),
            actor_id=_ACTOR_ID,
        )

        assert kind.id == _DAY_TOKENS

    def test_empty_source(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(errors.InvalidSourceEntitlement):
            domain.validate_source_change(
                source=EntitlementSourceId(""),
                kind_id=_DAY_TOKENS,
                granted=True,
                value=10,
                starts_at=now,
                expires_at=now + datetime.timedelta(days=1),
                actor_id=_ACTOR_ID,
            )

    def test_granted_requires_value(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(errors.InvalidSourceEntitlement):
            domain.validate_source_change(
                source=EntitlementSourceId("test"),
                kind_id=_DAY_TOKENS,
                granted=True,
                value=None,
                starts_at=now,
                expires_at=now + datetime.timedelta(days=1),
                actor_id=_ACTOR_ID,
            )

    def test_revoked_requires_no_value(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(errors.InvalidSourceEntitlement):
            domain.validate_source_change(
                source=EntitlementSourceId("test"),
                kind_id=_DAY_TOKENS,
                granted=False,
                value=10,
                starts_at=now,
                expires_at=now + datetime.timedelta(days=1),
                actor_id=_ACTOR_ID,
            )

    def test_timestamps_require_utc_offsets(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(errors.InvalidSourceEntitlement):
            domain.validate_source_change(
                source=EntitlementSourceId("test"),
                kind_id=_DAY_TOKENS,
                granted=True,
                value=10,
                starts_at=now.replace(tzinfo=None),
                expires_at=now + datetime.timedelta(days=1),
                actor_id=_ACTOR_ID,
            )

    def test_expiration_requires_utc_offset(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(errors.InvalidSourceEntitlement):
            domain.validate_source_change(
                source=EntitlementSourceId("test"),
                kind_id=_DAY_TOKENS,
                granted=True,
                value=10,
                starts_at=now,
                expires_at=(now + datetime.timedelta(days=1)).replace(tzinfo=None),
                actor_id=_ACTOR_ID,
            )

    def test_activation_must_be_before_expiration(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(errors.InvalidSourceEntitlement):
            domain.validate_source_change(
                source=EntitlementSourceId("test"),
                kind_id=_DAY_TOKENS,
                granted=True,
                value=10,
                starts_at=now,
                expires_at=now,
                actor_id=_ACTOR_ID,
            )

    def test_actor_id_must_not_be_empty(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(errors.InvalidActorId):
            domain.validate_source_change(
                source=EntitlementSourceId("test"),
                kind_id=_DAY_TOKENS,
                granted=True,
                value=10,
                starts_at=now,
                expires_at=now + datetime.timedelta(days=1),
                actor_id=SerializedId(" "),
            )

    def test_empty_actor_id(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)

        with pytest.raises(errors.InvalidActorId):
            domain.validate_source_change(
                source=EntitlementSourceId("test"),
                kind_id=_DAY_TOKENS,
                granted=True,
                value=10,
                starts_at=now,
                expires_at=now + datetime.timedelta(days=1),
                actor_id=SerializedId(""),
            )


class TestMergeValues:
    @pytest.mark.parametrize(
        ("policy", "expected"),
        [(MergePolicy.max, 7), (MergePolicy.min, 2), (MergePolicy.sum, 14)],
    )
    def test_policies(self, policy: MergePolicy, expected: int) -> None:
        assert domain.merge_values(policy, [5, 2, 7]) == expected

    @pytest.mark.parametrize(
        ("policy", "expected"),
        [(MergePolicy.max, 5), (MergePolicy.min, 5), (MergePolicy.sum, 10)],
    )
    def test_duplicate_values(self, policy: MergePolicy, expected: int) -> None:
        assert domain.merge_values(policy, [5, 5]) == expected

    def test_empty_values(self) -> None:
        with pytest.raises(errors.InvalidMergeValues, match="At least one"):
            domain.merge_values(MergePolicy.max, [])

    def test_unsupported_policy(self) -> None:
        with pytest.raises(AssertionError, match="Unsupported"):
            domain.merge_values(cast(MergePolicy, "unsupported"), [1])


class TestBuildEffectiveTimeline:
    def test_empty_source_entitlements(self) -> None:
        assert (
            domain.build_effective_timeline(
                user_id=new_user_id(),
                kind_id=_DAY_TOKENS,
                merge_policy=MergePolicy.max,
                source_entitlements=[],
                evaluation_time=datetime.datetime.now(tz=datetime.UTC),
            )
            == []
        )

    def test_merges_boundaries_and_coalesces_equal_values(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        first = make_source_entitlement(
            user_id=user_id,
            source=EntitlementSourceId("first"),
            value=10,
            starts_at=now - datetime.timedelta(days=2),
            expires_at=now + datetime.timedelta(days=2),
        )
        second = make_source_entitlement(
            user_id=user_id,
            source=EntitlementSourceId("second"),
            value=20,
            starts_at=now + datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=3),
        )

        intervals = domain.build_effective_timeline(
            user_id=user_id,
            kind_id=_DAY_TOKENS,
            merge_policy=MergePolicy.max,
            source_entitlements=[first, second],
            evaluation_time=now,
        )

        assert [(interval.value, interval.starts_at, interval.expires_at) for interval in intervals] == [
            (10, first.starts_at, second.starts_at),
            (20, second.starts_at, second.expires_at),
        ]

    def test_skips_expired_state(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        expired = make_source_entitlement(
            user_id=user_id,
            starts_at=now - datetime.timedelta(days=2),
            expires_at=now - datetime.timedelta(days=1),
        )

        assert (
            domain.build_effective_timeline(
                user_id=user_id,
                kind_id=_DAY_TOKENS,
                merge_policy=MergePolicy.max,
                source_entitlements=[expired],
                evaluation_time=now,
            )
            == []
        )

    def test_skips_revoked_state(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        revoked = make_source_entitlement(
            user_id=user_id,
            source=EntitlementSourceId("revoked"),
            granted=False,
            value=None,
        )

        assert (
            domain.build_effective_timeline(
                user_id=user_id,
                kind_id=_DAY_TOKENS,
                merge_policy=MergePolicy.max,
                source_entitlements=[revoked],
                evaluation_time=now,
            )
            == []
        )

    def test_preserves_gap_between_disjoint_grants(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        first = make_source_entitlement(
            user_id=user_id,
            source=EntitlementSourceId("first"),
            starts_at=now,
            expires_at=now + datetime.timedelta(days=1),
        )
        second = make_source_entitlement(
            user_id=user_id,
            source=EntitlementSourceId("second"),
            starts_at=now + datetime.timedelta(days=2),
            expires_at=now + datetime.timedelta(days=3),
        )

        intervals = domain.build_effective_timeline(
            user_id=user_id,
            kind_id=_DAY_TOKENS,
            merge_policy=MergePolicy.max,
            source_entitlements=[first, second],
            evaluation_time=now,
        )

        assert [(interval.starts_at, interval.expires_at) for interval in intervals] == [
            (first.starts_at, first.expires_at),
            (second.starts_at, second.expires_at),
        ]

    def test_skips_interval_expiring_at_evaluation_time(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)
        expired = make_source_entitlement(
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now,
        )

        assert (
            domain.build_effective_timeline(
                user_id=expired.user_id,
                kind_id=expired.kind_id,
                merge_policy=MergePolicy.max,
                source_entitlements=[expired],
                evaluation_time=now,
            )
            == []
        )


class TestEffectiveStateAt:
    def test_empty_intervals(self) -> None:
        assert domain.effective_state_at([], datetime.datetime.now(tz=datetime.UTC)) == (False, None)

    def test_half_open_interval(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)
        interval = make_effective_entitlement_interval(
            user_id=new_user_id(),
            kind_id=_DAY_TOKENS,
            value=10,
            starts_at=now,
            expires_at=now + datetime.timedelta(days=1),
        )

        assert domain.effective_state_at([interval], interval.starts_at) == (True, 10)
        assert domain.effective_state_at([interval], interval.expires_at) == (False, None)


class TestApplySourceChange:
    @pytest.mark.asyncio
    async def test_stores_new_source_state_and_effective_interval(self) -> None:
        source_state = make_source_entitlement()
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)

        async with (
            TableSizeDelta("en_source_entitlements", delta=1),
            TableSizeDelta("en_entitlements", delta=1),
            TableSizeDelta("a_records", delta=1),
        ):
            async with transaction() as transaction_execute:
                outcome = await domain._apply_source_change(
                    transaction_execute,
                    kind=domain.get_entitlement_kind(source_state.kind_id),
                    new_source_state=source_state,
                    evaluation_time=evaluation_time,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert outcome.changed
        assert outcome.effective_state == (True, source_state.value)
        assert len(outcome.effective_intervals) == 1


class TestEmitBusinessEvents:
    def test_emits_source_and_effective_state(self) -> None:
        source_state = make_source_entitlement()
        effective_interval = make_effective_entitlement_interval(
            user_id=source_state.user_id,
            kind_id=source_state.kind_id,
            value=cast(int, source_state.value),
            starts_at=source_state.starts_at,
            expires_at=source_state.expires_at,
        )
        outcome = domain._SourceChangeOutcome(
            changed=True,
            effective_state=(True, source_state.value),
            effective_intervals=[effective_interval],
        )

        with capture_logs() as logs:
            domain._emit_business_events(source_state, outcome)

        assert_logs_has_business_event(
            logs,
            "source_entitlement_changed",
            user_id=source_state.user_id,
            source=source_state.source,
            kind_id=source_state.kind_id.value,
            granted=True,
            value=source_state.value,
            starts_at=source_state.starts_at.isoformat(),
            expires_at=source_state.expires_at.isoformat(),
        )
        assert_logs_has_business_event(
            logs,
            "entitlement_changed",
            user_id=source_state.user_id,
            kind_id=source_state.kind_id.value,
            granted=True,
            value=source_state.value,
            new_effective_intervals=[
                {
                    "value": effective_interval.value,
                    "starts_at": effective_interval.starts_at.isoformat(),
                    "expires_at": effective_interval.expires_at.isoformat(),
                }
            ],
        )


class TestChangeSourceEntitlement:
    @pytest.mark.asyncio
    async def test_invalid_input_does_not_change_persistence(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)

        async with TableSizeNotChanged("en_source_entitlements"):
            async with TableSizeNotChanged("en_entitlements"):
                async with TableSizeNotChanged("a_records"):
                    with pytest.raises(errors.InvalidSourceEntitlement):
                        await domain.change_source_entitlement(
                            source=EntitlementSourceId(""),
                            user_id=user_id,
                            kind_id=_DAY_TOKENS,
                            granted=True,
                            value=10,
                            starts_at=now,
                            expires_at=now + datetime.timedelta(days=1),
                            actor_kind=_ACTOR_KIND,
                            actor_id=_ACTOR_ID,
                        )

    @pytest.mark.asyncio
    async def test_stores_state_timeline_audit_and_events(self) -> None:
        user_id = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=2)

        with capture_logs() as logs:
            async with TableSizeDelta("en_source_entitlements", delta=1):
                async with TableSizeDelta("en_entitlements", delta=1):
                    async with TableSizeDelta("a_records", delta=1):
                        state = await domain.change_source_entitlement(
                            source=_SOURCE,
                            user_id=user_id,
                            kind_id=_DAY_TOKENS,
                            granted=True,
                            value=10,
                            starts_at=starts_at,
                            expires_at=expires_at,
                            actor_kind=_ACTOR_KIND,
                            actor_id=_ACTOR_ID,
                        )

        assert state == (True, 10)
        expected_source = make_source_entitlement(
            user_id=user_id,
            starts_at=starts_at,
            expires_at=expires_at,
        )
        assert (
            await operations.load_source_entitlement(
                execute,
                user_id,
                _DAY_TOKENS,
                EntitlementSourceId("test"),
            )
            == expected_source
        )
        expected_interval = make_effective_entitlement_interval(
            user_id=user_id,
            kind_id=_DAY_TOKENS,
            value=10,
            starts_at=starts_at,
            expires_at=expires_at,
        )
        intervals = await operations.load_effective_intervals(
            execute,
            user_id,
            _DAY_TOKENS,
            ending_after=starts_at,
        )
        assert intervals == [expected_interval]
        records = await audit_domain.load_records_for_subject(
            execute,
            subject_kind=AuditEntityKind.user,
            subject_id=SerializedId(str(user_id)),
        )
        assert len(records) == 1
        assert records[0].attributes == {
            "source": "test",
            "kind_id": _DAY_TOKENS.value,
            "previous_source_state": None,
            "new_source_state": cast(dict[str, object], expected_source.model_dump(mode="json")),
            "previous_effective_intervals": [],
            "new_effective_intervals": [cast(dict[str, object], expected_interval.model_dump(mode="json"))],
        }
        assert_logs_has_business_event(
            logs,
            "source_entitlement_changed",
            user_id=user_id,
            source="test",
            kind_id=_DAY_TOKENS.value,
            granted=True,
            value=10,
            starts_at=starts_at.isoformat(),
            expires_at=expires_at.isoformat(),
        )
        assert_logs_has_business_event(
            logs,
            "entitlement_changed",
            user_id=user_id,
            kind_id=_DAY_TOKENS.value,
            granted=True,
            value=10,
            new_effective_intervals=[
                {"value": 10, "starts_at": starts_at.isoformat(), "expires_at": expires_at.isoformat()}
            ],
        )

    @pytest.mark.asyncio
    async def test_identical_state_is_no_op(self) -> None:
        user_id = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=2)
        await domain.change_source_entitlement(
            source=_SOURCE,
            user_id=user_id,
            kind_id=_DAY_TOKENS,
            granted=True,
            value=10,
            starts_at=starts_at,
            expires_at=expires_at,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        with capture_logs() as logs:
            async with TableSizeNotChanged("en_source_entitlements"):
                async with TableSizeNotChanged("en_entitlements"):
                    async with TableSizeNotChanged("a_records"):
                        state = await domain.change_source_entitlement(
                            source=_SOURCE,
                            user_id=user_id,
                            kind_id=_DAY_TOKENS,
                            granted=True,
                            value=10,
                            starts_at=starts_at,
                            expires_at=expires_at,
                            actor_kind=_ACTOR_KIND,
                            actor_id=_ACTOR_ID,
                        )

        assert state == (True, 10)
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_multiple_sources_merge_and_revoke_independently(self) -> None:
        user_id = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=3)
        async with (
            TableSizeDelta("en_source_entitlements", delta=1),
            TableSizeDelta("en_entitlements", delta=1),
            TableSizeDelta("a_records", delta=1),
        ):
            await domain.change_source_entitlement(
                source=EntitlementSourceId("first"),
                user_id=user_id,
                kind_id=_DAY_TOKENS,
                granted=True,
                value=10,
                starts_at=starts_at,
                expires_at=expires_at,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        async with (
            TableSizeDelta("en_source_entitlements", delta=1),
            TableSizeNotChanged("en_entitlements"),
            TableSizeDelta("a_records", delta=1),
        ):
            state = await domain.change_source_entitlement(
                source=EntitlementSourceId("second"),
                user_id=user_id,
                kind_id=_DAY_TOKENS,
                granted=True,
                value=20,
                starts_at=starts_at,
                expires_at=expires_at,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )
        assert state == (True, 20)

        async with (
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeDelta("a_records", delta=1),
        ):
            state = await domain.change_source_entitlement(
                source=EntitlementSourceId("second"),
                user_id=user_id,
                kind_id=_DAY_TOKENS,
                granted=False,
                value=None,
                starts_at=starts_at,
                expires_at=expires_at,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert state == (True, 10)
        sources = await operations.load_source_entitlements(execute, user_id, _DAY_TOKENS)
        assert len(sources) == 2
        assert {source.source: source.granted for source in sources} == {"first": True, "second": False}

    @pytest.mark.asyncio
    async def test_future_state_replaces_current_source_contribution(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        async with (
            TableSizeDelta("en_source_entitlements", delta=1),
            TableSizeDelta("en_entitlements", delta=1),
            TableSizeDelta("a_records", delta=1),
        ):
            await domain.change_source_entitlement(
                source=_SOURCE,
                user_id=user_id,
                kind_id=_DAY_TOKENS,
                granted=True,
                value=10,
                starts_at=now - datetime.timedelta(days=1),
                expires_at=now + datetime.timedelta(days=1),
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        future_start = now + datetime.timedelta(days=2)
        async with (
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeDelta("a_records", delta=1),
        ):
            state = await domain.change_source_entitlement(
                source=_SOURCE,
                user_id=user_id,
                kind_id=_DAY_TOKENS,
                granted=True,
                value=20,
                starts_at=future_start,
                expires_at=future_start + datetime.timedelta(days=1),
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert state == (False, None)
        intervals = await operations.load_effective_intervals(
            execute,
            user_id,
            _DAY_TOKENS,
            ending_after=now,
        )
        assert [(interval.value, interval.starts_at) for interval in intervals] == [(20, future_start)]

    @pytest.mark.asyncio
    async def test_audit_failure_rolls_back_without_events(self, mocker: MockerFixture) -> None:
        user_id = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=2)
        mocker.patch.object(audit_domain, "record", side_effect=RuntimeError("audit failed"))

        with capture_logs() as logs:
            async with TableSizeNotChanged("en_source_entitlements"):
                async with TableSizeNotChanged("en_entitlements"):
                    async with TableSizeNotChanged("a_records"):
                        with pytest.raises(RuntimeError, match="audit failed"):
                            await domain.change_source_entitlement(
                                source=_SOURCE,
                                user_id=user_id,
                                kind_id=_DAY_TOKENS,
                                granted=True,
                                value=10,
                                starts_at=starts_at,
                                expires_at=expires_at,
                                actor_kind=_ACTOR_KIND,
                                actor_id=_ACTOR_ID,
                            )

        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")


class TestCleanupExpiredEntitlements:
    @pytest.mark.asyncio
    async def test_no_expired_rows(self) -> None:
        await clear_effective_intervals()

        async with TableSizeNotChanged("en_entitlements"):
            deleted = await domain.cleanup_expired_entitlements()

        assert deleted == 0

    @pytest.mark.asyncio
    async def test_deletes_expired_effective_rows_only(self) -> None:
        await clear_effective_intervals()

        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        expired = make_effective_entitlement_interval(
            user_id=user_id,
            kind_id=_DAY_TOKENS,
            value=10,
            starts_at=now - datetime.timedelta(days=2),
            expires_at=now - datetime.timedelta(days=1),
        )
        source = make_source_entitlement(
            user_id=user_id,
            kind_id=_DAY_TOKENS,
            starts_at=expired.starts_at,
            expires_at=expired.expires_at,
        )
        await operations.upsert_source_entitlement(execute, source)

        async with transaction() as transaction_execute:
            await operations.replace_effective_intervals(transaction_execute, user_id, _DAY_TOKENS, [expired])

        async with TableSizeNotChanged("en_source_entitlements"):
            async with TableSizeDelta("en_entitlements", delta=-1):
                deleted = await domain.cleanup_expired_entitlements()

        assert deleted == 1
        assert await operations.load_source_entitlement(execute, user_id, _DAY_TOKENS, source.source) == source


class TestGetEntitlements:
    @pytest.mark.asyncio
    async def test_returns_every_user_and_selected_kind(self) -> None:
        entitled_user = new_user_id()
        other_user = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=2)
        await domain.change_source_entitlement(
            source=_SOURCE,
            user_id=entitled_user,
            kind_id=_DAY_TOKENS,
            granted=True,
            value=10,
            starts_at=starts_at,
            expires_at=expires_at,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        checked = await domain.get_entitlements(
            [entitled_user, other_user],
            [_DAY_TOKENS, _MONTH_TOKENS],
        )

        assert checked == {
            entitled_user: {_DAY_TOKENS: True, _MONTH_TOKENS: False},
            other_user: {_DAY_TOKENS: False, _MONTH_TOKENS: False},
        }

    @pytest.mark.asyncio
    async def test_empty_kind_list_selects_all_configured_kinds(self) -> None:
        user_id = new_user_id()

        assert await domain.get_entitlements([user_id], []) == {user_id: {_DAY_TOKENS: False, _MONTH_TOKENS: False}}

    @pytest.mark.asyncio
    async def test_empty_user_list(self) -> None:
        assert await domain.get_entitlements([], [_DAY_TOKENS]) == {}

    @pytest.mark.asyncio
    async def test_duplicate_user_ids(self) -> None:
        user_id = new_user_id()

        assert await domain.get_entitlements([user_id, user_id], [_DAY_TOKENS]) == {user_id: {_DAY_TOKENS: False}}

    @pytest.mark.asyncio
    async def test_duplicate_kind_ids(self) -> None:
        user_id = new_user_id()

        assert await domain.get_entitlements([user_id], [_DAY_TOKENS, _DAY_TOKENS]) == {user_id: {_DAY_TOKENS: False}}

    @pytest.mark.asyncio
    async def test_unconfigured_kind(self, mocker: MockerFixture) -> None:
        mocker.patch.object(
            entitlement_entities,
            "ENTITLEMENT_KINDS",
            (entitlement_entities.ENTITLEMENT_KINDS[0],),
        )

        with pytest.raises(errors.UnknownEntitlementKind):
            await domain.get_entitlements([new_user_id()], [_MONTH_TOKENS])

    @pytest.mark.asyncio
    async def test_query_does_not_remove_expired_rows(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        expired = make_effective_entitlement_interval(
            user_id=user_id,
            kind_id=_DAY_TOKENS,
            value=10,
            starts_at=now - datetime.timedelta(days=2),
            expires_at=now - datetime.timedelta(days=1),
        )

        async with transaction() as transaction_execute:
            await operations.replace_effective_intervals(transaction_execute, user_id, _DAY_TOKENS, [expired])

        async with TableSizeNotChanged("en_entitlements"):
            checked = await domain.get_entitlements([user_id], [_DAY_TOKENS])

        assert checked == {user_id: {_DAY_TOKENS: False}}
