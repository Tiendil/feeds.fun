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
from ffun.domain.datetime_intervals import LIFETIME_INTERVAL_END_MARKER
from ffun.domain.domain import new_user_id
from ffun.domain.entities import SerializedId
from ffun.entitlements import domain
from ffun.entitlements import entities as entitlement_entities
from ffun.entitlements import errors, operations
from ffun.entitlements.entities import (
    EntitlementKindId,
    EntitlementSourceId,
    EntitlementTransactionId,
    MergePolicy,
)
from ffun.entitlements.tests.helpers import clear_effective_intervals
from ffun.entitlements.tests.make import make_effective_entitlement_interval, make_source_entitlement

_DAY_TOKENS = EntitlementKindId.day_tokens
_MONTH_TOKENS = EntitlementKindId.month_tokens
_LIFETIME_TOKENS = EntitlementKindId.lifetime_tokens
_SOURCE = EntitlementSourceId("test")
_TRANSACTION = EntitlementTransactionId("test-transaction")
_ACTOR_KIND = AuditEntityKind.admin
_ACTOR_ID = SerializedId("test-admin")


class TestGetEntitlementKind:
    @pytest.mark.parametrize(
        ("kind_id", "merge_policy", "is_lifetime"),
        [
            (_DAY_TOKENS, MergePolicy.max, False),
            (_MONTH_TOKENS, MergePolicy.max, False),
            (_LIFETIME_TOKENS, MergePolicy.sum, True),
        ],
    )
    def test_known_kind(
        self,
        kind_id: EntitlementKindId,
        merge_policy: MergePolicy,
        is_lifetime: bool,
    ) -> None:
        kind = domain.get_entitlement_kind(kind_id)

        assert kind.merge_policy == merge_policy
        assert kind.is_lifetime == is_lifetime

    def test_unconfigured_kind(self, mocker: MockerFixture) -> None:
        mocker.patch.object(entitlement_entities, "ENTITLEMENT_KINDS", (entitlement_entities.ENTITLEMENT_KINDS[0],))

        with pytest.raises(errors.UnknownEntitlementKind):
            domain.get_entitlement_kind(_MONTH_TOKENS)


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

    def test_revocation_is_an_exclusive_boundary(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        revoked_at = now + datetime.timedelta(days=1)
        entitlement = make_source_entitlement(
            user_id=user_id,
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=2),
            revoked_at=revoked_at,
        )

        intervals = domain.build_effective_timeline(
            user_id=user_id,
            kind_id=_DAY_TOKENS,
            merge_policy=MergePolicy.max,
            source_entitlements=[entitlement],
            evaluation_time=now,
        )

        assert [(interval.starts_at, interval.expires_at) for interval in intervals] == [
            (entitlement.starts_at, revoked_at)
        ]

    def test_sum_policy_combines_same_source_transactions(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        first = make_source_entitlement(
            user_id=user_id,
            kind_id=_LIFETIME_TOKENS,
            value=10,
            starts_at=now,
            expires_at=LIFETIME_INTERVAL_END_MARKER,
        )
        second = first.replace(transaction_id=EntitlementTransactionId("second"), value=20)

        intervals = domain.build_effective_timeline(
            user_id=user_id,
            kind_id=_LIFETIME_TOKENS,
            merge_policy=MergePolicy.sum,
            source_entitlements=[first, second],
            evaluation_time=now,
        )

        assert [(interval.value, interval.starts_at, interval.expires_at) for interval in intervals] == [
            (30, now, LIFETIME_INTERVAL_END_MARKER)
        ]

    def test_skips_intervals_ending_at_evaluation_time(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)
        expired = make_source_entitlement(
            starts_at=now - datetime.timedelta(days=2),
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

    def test_returns_active_interval_state(self) -> None:
        starts_at = datetime.datetime.now(tz=datetime.UTC)
        interval = make_effective_entitlement_interval(
            value=17,
            starts_at=starts_at,
            expires_at=starts_at + datetime.timedelta(days=1),
        )

        assert domain.effective_state_at([interval], starts_at) == (True, 17)

    def test_interval_end_is_exclusive(self) -> None:
        starts_at = datetime.datetime.now(tz=datetime.UTC)
        expires_at = starts_at + datetime.timedelta(days=1)
        interval = make_effective_entitlement_interval(starts_at=starts_at, expires_at=expires_at)

        assert domain.effective_state_at([interval], expires_at) == (False, None)


class TestRebuildAfterSourceChange:
    @pytest.mark.asyncio
    async def test_rebuilds_effective_state_and_records_audit(self) -> None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)
        source_state = make_source_entitlement(
            starts_at=evaluation_time - datetime.timedelta(days=1),
            expires_at=evaluation_time + datetime.timedelta(days=1),
        )
        await operations.insert_source_entitlement(execute, source_state)

        async with transaction() as transaction_execute:
            outcome = await domain._rebuild_after_source_change(
                transaction_execute,
                kind=domain.get_entitlement_kind(source_state.kind_id),
                previous_source_state=None,
                new_source_state=source_state,
                previous_effective_intervals=[],
                evaluation_time=evaluation_time,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert outcome.changed
        assert outcome.effective_state == (True, source_state.value)
        assert outcome.source_state == source_state
        assert (
            await operations.load_effective_intervals(
                execute,
                source_state.user_id,
                source_state.kind_id,
                ending_after=evaluation_time,
            )
            == outcome.effective_intervals
        )
        records = await audit_domain.load_records_for_subject(
            execute,
            subject_kind=AuditEntityKind.user,
            subject_id=SerializedId(str(source_state.user_id)),
        )
        assert records[-1].attributes["new_source_state"] == cast(
            dict[str, object], source_state.model_dump(mode="json")
        )


class TestUnchangedOutcome:
    def test_preserves_source_and_intervals(self) -> None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)
        source_state = make_source_entitlement()
        interval = make_effective_entitlement_interval(
            user_id=source_state.user_id,
            kind_id=source_state.kind_id,
            value=source_state.value,
            starts_at=evaluation_time - datetime.timedelta(days=1),
            expires_at=evaluation_time + datetime.timedelta(days=1),
        )

        outcome = domain._unchanged_outcome(source_state, [interval], evaluation_time)

        assert not outcome.changed
        assert outcome.effective_state == (True, source_state.value)
        assert outcome.effective_intervals == [interval]
        assert outcome.source_state == source_state


class TestApplySourceGrant:
    @pytest.mark.asyncio
    async def test_inserts_new_source_and_rebuilds(self) -> None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)
        source_state = make_source_entitlement(
            starts_at=evaluation_time - datetime.timedelta(days=1),
            expires_at=evaluation_time + datetime.timedelta(days=1),
        )

        async with transaction() as transaction_execute:
            outcome = await domain._apply_source_grant(
                transaction_execute,
                kind=domain.get_entitlement_kind(source_state.kind_id),
                source_state=source_state,
                evaluation_time=evaluation_time,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert outcome.changed
        assert outcome.effective_state == (True, source_state.value)
        assert outcome.source_state == source_state
        assert (
            await operations.load_source_entitlement(
                execute,
                source_state.user_id,
                source_state.kind_id,
                source_state.source,
                source_state.transaction_id,
            )
            == source_state
        )

    @pytest.mark.asyncio
    async def test_identical_existing_source_is_unchanged(self) -> None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)
        source_state = make_source_entitlement(
            starts_at=evaluation_time - datetime.timedelta(days=1),
            expires_at=evaluation_time + datetime.timedelta(days=1),
        )
        async with transaction() as transaction_execute:
            await domain._apply_source_grant(
                transaction_execute,
                kind=domain.get_entitlement_kind(source_state.kind_id),
                source_state=source_state,
                evaluation_time=evaluation_time,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )
        async with (
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            async with transaction() as transaction_execute:
                outcome = await domain._apply_source_grant(
                    transaction_execute,
                    kind=domain.get_entitlement_kind(source_state.kind_id),
                    source_state=source_state,
                    evaluation_time=evaluation_time,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert not outcome.changed
        assert outcome.source_state == source_state

    @pytest.mark.asyncio
    async def test_changed_immutable_field_conflicts(self) -> None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)
        source_state = make_source_entitlement(value=10)
        async with transaction() as transaction_execute:
            await domain._apply_source_grant(
                transaction_execute,
                kind=domain.get_entitlement_kind(source_state.kind_id),
                source_state=source_state,
                evaluation_time=evaluation_time,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        async with (
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            with pytest.raises(errors.SourceEntitlementConflict):
                async with transaction() as transaction_execute:
                    await domain._apply_source_grant(
                        transaction_execute,
                        kind=domain.get_entitlement_kind(source_state.kind_id),
                        source_state=source_state.replace(value=20),
                        evaluation_time=evaluation_time,
                        actor_kind=_ACTOR_KIND,
                        actor_id=_ACTOR_ID,
                    )


class TestApplySourceRevocation:
    @pytest.mark.asyncio
    async def test_missing_source_fails(self) -> None:
        source_state = make_source_entitlement()

        async with (
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            with pytest.raises(errors.SourceEntitlementNotFound):
                async with transaction() as transaction_execute:
                    await domain._apply_source_revocation(
                        transaction_execute,
                        kind=domain.get_entitlement_kind(source_state.kind_id),
                        source=source_state.source,
                        transaction_id=source_state.transaction_id,
                        user_id=source_state.user_id,
                        evaluation_time=datetime.datetime.now(tz=datetime.UTC),
                        actor_kind=_ACTOR_KIND,
                        actor_id=_ACTOR_ID,
                    )

    @pytest.mark.asyncio
    async def test_revokes_source_and_rebuilds(self) -> None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)
        source_state = make_source_entitlement(
            starts_at=evaluation_time - datetime.timedelta(days=1),
            expires_at=evaluation_time + datetime.timedelta(days=1),
        )
        revoked_state = source_state.to_revoked(revoked_at=evaluation_time)
        async with transaction() as transaction_execute:
            await domain._apply_source_grant(
                transaction_execute,
                kind=domain.get_entitlement_kind(source_state.kind_id),
                source_state=source_state,
                evaluation_time=evaluation_time,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )
        async with transaction() as transaction_execute:
            outcome = await domain._apply_source_revocation(
                transaction_execute,
                kind=domain.get_entitlement_kind(source_state.kind_id),
                source=source_state.source,
                transaction_id=source_state.transaction_id,
                user_id=source_state.user_id,
                evaluation_time=evaluation_time,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert outcome.changed
        assert outcome.effective_state == (False, None)
        assert outcome.effective_intervals == []
        assert outcome.source_state == revoked_state
        assert (
            await operations.load_source_entitlement(
                execute,
                source_state.user_id,
                source_state.kind_id,
                source_state.source,
                source_state.transaction_id,
            )
            == revoked_state
        )

    @pytest.mark.asyncio
    async def test_already_revoked_source_is_unchanged(self) -> None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)
        source_state = make_source_entitlement()
        async with transaction() as transaction_execute:
            await domain._apply_source_grant(
                transaction_execute,
                kind=domain.get_entitlement_kind(source_state.kind_id),
                source_state=source_state,
                evaluation_time=evaluation_time,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )
        async with transaction() as transaction_execute:
            first = await domain._apply_source_revocation(
                transaction_execute,
                kind=domain.get_entitlement_kind(source_state.kind_id),
                source=source_state.source,
                transaction_id=source_state.transaction_id,
                user_id=source_state.user_id,
                evaluation_time=evaluation_time,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )
        async with (
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            async with transaction() as transaction_execute:
                outcome = await domain._apply_source_revocation(
                    transaction_execute,
                    kind=domain.get_entitlement_kind(source_state.kind_id),
                    source=source_state.source,
                    transaction_id=source_state.transaction_id,
                    user_id=source_state.user_id,
                    evaluation_time=evaluation_time + datetime.timedelta(days=1),
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert not outcome.changed
        assert outcome.source_state == first.source_state


class TestEmitBusinessEvents:
    def test_emits_source_and_effective_state_events(self) -> None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)
        source_state = make_source_entitlement(
            starts_at=evaluation_time - datetime.timedelta(days=1),
            expires_at=evaluation_time + datetime.timedelta(days=1),
        )
        interval = make_effective_entitlement_interval(
            user_id=source_state.user_id,
            kind_id=source_state.kind_id,
            value=source_state.value,
            starts_at=source_state.starts_at,
            expires_at=source_state.expires_at,
        )
        outcome = domain._SourceChangeOutcome(
            changed=True,
            effective_state=(True, source_state.value),
            effective_intervals=[interval],
            source_state=source_state,
        )

        with capture_logs() as logs:
            domain._emit_business_events(outcome)

        assert_logs_has_business_event(
            logs,
            "source_entitlement_changed",
            user_id=source_state.user_id,
            source=source_state.source,
            transaction_id=source_state.transaction_id,
            kind_id=source_state.kind_id,
            granted=True,
        )
        assert_logs_has_business_event(
            logs,
            "entitlement_changed",
            user_id=source_state.user_id,
            kind_id=source_state.kind_id,
            granted=True,
            value=source_state.value,
        )


class TestGrantSourceEntitlement:
    @pytest.mark.asyncio
    async def test_invalid_policy_does_not_change_persistence(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        source_entitlement = make_source_entitlement(
            user_id=user_id,
            kind_id=_LIFETIME_TOKENS,
            starts_at=now,
            expires_at=now + datetime.timedelta(days=1),
        )

        async with TableSizeNotChanged("en_source_entitlements"):
            async with TableSizeNotChanged("en_entitlements"):
                async with TableSizeNotChanged("a_records"):
                    with pytest.raises(errors.InvalidSourceEntitlement):
                        await domain.grant_source_entitlement(
                            source_entitlement,
                            actor_kind=_ACTOR_KIND,
                            actor_id=_ACTOR_ID,
                        )

    @pytest.mark.asyncio
    async def test_stores_grant_timeline_audit_and_events(self) -> None:
        user_id = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=2)
        source_entitlement = make_source_entitlement(
            user_id=user_id,
            starts_at=starts_at,
            expires_at=expires_at,
        )

        with capture_logs() as logs:
            async with (
                TableSizeDelta("en_source_entitlements", delta=1),
                TableSizeDelta("en_entitlements", delta=1),
                TableSizeDelta("a_records", delta=1),
            ):
                state = await domain.grant_source_entitlement(
                    source_entitlement,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert state == (True, 10)
        assert (
            await operations.load_source_entitlement(
                execute,
                user_id,
                _DAY_TOKENS,
                _SOURCE,
                _TRANSACTION,
            )
            == source_entitlement
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
        assert records[0].attributes == {
            "source": "test",
            "transaction_id": "test-transaction",
            "kind_id": _DAY_TOKENS.value,
            "previous_source_state": None,
            "new_source_state": cast(dict[str, object], source_entitlement.model_dump(mode="json")),
            "previous_effective_intervals": [],
            "new_effective_intervals": [cast(dict[str, object], expected_interval.model_dump(mode="json"))],
        }
        assert_logs_has_business_event(
            logs,
            "source_entitlement_changed",
            user_id=user_id,
            source="test",
            transaction_id="test-transaction",
            kind_id=_DAY_TOKENS.value,
            granted=True,
            value=10,
            starts_at=starts_at.isoformat(),
            expires_at=expires_at.isoformat(),
            revoked_at=None,
        )

    @pytest.mark.asyncio
    async def test_identical_grant_is_no_op(self) -> None:
        user_id = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=2)
        source_entitlement = make_source_entitlement(
            user_id=user_id,
            starts_at=starts_at,
            expires_at=expires_at,
        )
        await domain.grant_source_entitlement(
            source_entitlement,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                state = await domain.grant_source_entitlement(
                    source_entitlement,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert state == (True, 10)
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_reusing_identity_with_different_immutable_fields_fails(self) -> None:
        user_id = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=2)
        source_entitlement = make_source_entitlement(
            user_id=user_id,
            starts_at=starts_at,
            expires_at=expires_at,
        )
        await domain.grant_source_entitlement(
            source_entitlement,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        async with (
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            with pytest.raises(errors.SourceEntitlementConflict):
                await domain.grant_source_entitlement(
                    source_entitlement.replace(value=20),
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

    @pytest.mark.asyncio
    async def test_future_grant_does_not_replace_current_grant(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        await domain.grant_source_entitlement(
            make_source_entitlement(
                user_id=user_id,
                starts_at=now - datetime.timedelta(days=1),
                expires_at=now + datetime.timedelta(days=1),
            ),
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )
        future_start = now + datetime.timedelta(days=2)

        state = await domain.grant_source_entitlement(
            make_source_entitlement(
                user_id=user_id,
                transaction_id=EntitlementTransactionId("future"),
                value=20,
                starts_at=future_start,
                expires_at=future_start + datetime.timedelta(days=1),
            ),
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        assert state == (True, 10)
        intervals = await operations.load_effective_intervals(execute, user_id, _DAY_TOKENS, ending_after=now)
        assert [(interval.value, interval.starts_at) for interval in intervals] == [
            (10, now - datetime.timedelta(days=1)),
            (20, future_start),
        ]

    @pytest.mark.asyncio
    async def test_lifetime_transactions_sum(self) -> None:
        user_id = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        await domain.grant_source_entitlement(
            make_source_entitlement(
                user_id=user_id,
                kind_id=_LIFETIME_TOKENS,
                value=10,
                starts_at=starts_at,
                expires_at=LIFETIME_INTERVAL_END_MARKER,
            ),
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        state = await domain.grant_source_entitlement(
            make_source_entitlement(
                user_id=user_id,
                transaction_id=EntitlementTransactionId("second"),
                kind_id=_LIFETIME_TOKENS,
                value=20,
                starts_at=starts_at,
                expires_at=LIFETIME_INTERVAL_END_MARKER,
            ),
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        assert state == (True, 30)

    @pytest.mark.asyncio
    async def test_audit_failure_rolls_back_without_events(self, mocker: MockerFixture) -> None:
        user_id = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=2)
        mocker.patch.object(audit_domain, "record", side_effect=RuntimeError("audit failed"))

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(RuntimeError, match="audit failed"):
                    await domain.grant_source_entitlement(
                        make_source_entitlement(
                            user_id=user_id,
                            starts_at=starts_at,
                            expires_at=expires_at,
                        ),
                        actor_kind=_ACTOR_KIND,
                        actor_id=_ACTOR_ID,
                    )

        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")


class TestRevokeSourceEntitlement:
    @pytest.mark.asyncio
    async def test_missing_grant_fails_without_changes(self) -> None:
        async with (
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            with pytest.raises(errors.SourceEntitlementNotFound):
                await domain.revoke_source_entitlement(
                    source=_SOURCE,
                    transaction_id=_TRANSACTION,
                    user_id=new_user_id(),
                    kind_id=_DAY_TOKENS,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

    @pytest.mark.asyncio
    async def test_revokes_grant_and_records_complete_change(self) -> None:
        user_id = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=2)
        previous_source = make_source_entitlement(user_id=user_id, starts_at=starts_at, expires_at=expires_at)
        await domain.grant_source_entitlement(
            previous_source,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeDelta("en_entitlements", delta=-1),
                TableSizeDelta("a_records", delta=1),
            ):
                state = await domain.revoke_source_entitlement(
                    source=_SOURCE,
                    transaction_id=_TRANSACTION,
                    user_id=user_id,
                    kind_id=_DAY_TOKENS,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert state == (False, None)
        revoked = await operations.load_source_entitlement(
            execute,
            user_id,
            _DAY_TOKENS,
            _SOURCE,
            _TRANSACTION,
        )
        assert revoked is not None
        assert revoked.revoked_at is not None
        assert revoked == previous_source.to_revoked(revoked_at=revoked.revoked_at)
        records = await audit_domain.load_records_for_subject(
            execute,
            subject_kind=AuditEntityKind.user,
            subject_id=SerializedId(str(user_id)),
        )
        assert records[-1].attributes["previous_source_state"] == cast(
            dict[str, object], previous_source.model_dump(mode="json")
        )
        assert records[-1].attributes["new_source_state"] == cast(dict[str, object], revoked.model_dump(mode="json"))
        assert records[-1].attributes["transaction_id"] == "test-transaction"
        assert_logs_has_business_event(
            logs,
            "source_entitlement_changed",
            user_id=user_id,
            source="test",
            transaction_id="test-transaction",
            kind_id=_DAY_TOKENS.value,
            granted=False,
            value=10,
            starts_at=starts_at.isoformat(),
            expires_at=expires_at.isoformat(),
            revoked_at=revoked.revoked_at.isoformat(),
        )

    @pytest.mark.asyncio
    async def test_repeated_revocation_is_no_op_and_preserves_timestamp(self) -> None:
        user_id = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=2)
        await domain.grant_source_entitlement(
            make_source_entitlement(user_id=user_id, starts_at=starts_at, expires_at=expires_at),
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )
        await domain.revoke_source_entitlement(
            source=_SOURCE,
            transaction_id=_TRANSACTION,
            user_id=user_id,
            kind_id=_DAY_TOKENS,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )
        first = await operations.load_source_entitlement(execute, user_id, _DAY_TOKENS, _SOURCE, _TRANSACTION)
        assert first is not None

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                state = await domain.revoke_source_entitlement(
                    source=_SOURCE,
                    transaction_id=_TRANSACTION,
                    user_id=user_id,
                    kind_id=_DAY_TOKENS,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        second = await operations.load_source_entitlement(execute, user_id, _DAY_TOKENS, _SOURCE, _TRANSACTION)
        assert state == (False, None)
        assert second == first
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_grant_retry_after_revocation_is_no_op(self) -> None:
        user_id = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=2)
        source_entitlement = make_source_entitlement(
            user_id=user_id,
            starts_at=starts_at,
            expires_at=expires_at,
        )
        await domain.grant_source_entitlement(
            source_entitlement,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )
        await domain.revoke_source_entitlement(
            source=_SOURCE,
            transaction_id=_TRANSACTION,
            user_id=user_id,
            kind_id=_DAY_TOKENS,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        async with (
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            state = await domain.grant_source_entitlement(
                source_entitlement,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert state == (False, None)

    @pytest.mark.asyncio
    async def test_revoking_one_transaction_preserves_other_grants(self) -> None:
        user_id = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=2)
        await domain.grant_source_entitlement(
            make_source_entitlement(
                user_id=user_id,
                value=10,
                starts_at=starts_at,
                expires_at=expires_at,
            ),
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )
        await domain.grant_source_entitlement(
            make_source_entitlement(
                user_id=user_id,
                transaction_id=EntitlementTransactionId("second"),
                value=20,
                starts_at=starts_at,
                expires_at=expires_at,
            ),
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        state = await domain.revoke_source_entitlement(
            source=_SOURCE,
            transaction_id=EntitlementTransactionId("second"),
            user_id=user_id,
            kind_id=_DAY_TOKENS,
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        assert state == (True, 10)
        sources = await operations.load_source_entitlements(execute, user_id, _DAY_TOKENS)
        assert {source.transaction_id: source.granted for source in sources} == {
            "test-transaction": True,
            "second": False,
        }


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
            starts_at=now - datetime.timedelta(days=2),
            expires_at=now - datetime.timedelta(days=1),
        )
        source = make_source_entitlement(
            user_id=user_id,
            starts_at=expired.starts_at,
            expires_at=expired.expires_at,
        )
        await operations.insert_source_entitlement(execute, source)
        async with transaction() as transaction_execute:
            await operations.replace_effective_intervals(transaction_execute, user_id, _DAY_TOKENS, [expired])

        async with TableSizeNotChanged("en_source_entitlements"):
            async with TableSizeDelta("en_entitlements", delta=-1):
                deleted = await domain.cleanup_expired_entitlements()

        assert deleted == 1


class TestGetEntitlements:
    @pytest.mark.asyncio
    async def test_returns_every_user_and_selected_kind(self) -> None:
        entitled_user = new_user_id()
        other_user = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=2)
        await domain.grant_source_entitlement(
            make_source_entitlement(
                user_id=entitled_user,
                starts_at=starts_at,
                expires_at=expires_at,
            ),
            actor_kind=_ACTOR_KIND,
            actor_id=_ACTOR_ID,
        )

        listed = await domain.get_entitlements([entitled_user, other_user], [_DAY_TOKENS, _MONTH_TOKENS])

        assert listed == {
            entitled_user: {
                _DAY_TOKENS: make_effective_entitlement_interval(
                    user_id=entitled_user,
                    kind_id=_DAY_TOKENS,
                    value=10,
                    starts_at=starts_at,
                    expires_at=expires_at,
                ),
                _MONTH_TOKENS: None,
            },
            other_user: {_DAY_TOKENS: None, _MONTH_TOKENS: None},
        }

    @pytest.mark.asyncio
    async def test_empty_kind_list_selects_all_configured_kinds(self) -> None:
        user_id = new_user_id()

        assert await domain.get_entitlements([user_id], []) == {
            user_id: {_DAY_TOKENS: None, _MONTH_TOKENS: None, _LIFETIME_TOKENS: None}
        }

    @pytest.mark.asyncio
    async def test_empty_user_list(self) -> None:
        assert await domain.get_entitlements([], [_DAY_TOKENS]) == {}

    @pytest.mark.asyncio
    async def test_duplicate_user_ids(self) -> None:
        user_id = new_user_id()

        assert await domain.get_entitlements([user_id, user_id], [_DAY_TOKENS]) == {user_id: {_DAY_TOKENS: None}}

    @pytest.mark.asyncio
    async def test_duplicate_kind_ids(self) -> None:
        user_id = new_user_id()

        assert await domain.get_entitlements([user_id], [_DAY_TOKENS, _DAY_TOKENS]) == {user_id: {_DAY_TOKENS: None}}

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
        interval = make_effective_entitlement_interval(
            starts_at=datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=2),
            expires_at=datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1),
        )
        async with transaction() as transaction_execute:
            await operations.replace_effective_intervals(
                transaction_execute,
                interval.user_id,
                interval.kind_id,
                [interval],
            )

        async with TableSizeNotChanged("en_entitlements"):
            listed = await domain.get_entitlements([interval.user_id], [interval.kind_id])

        assert listed == {interval.user_id: {interval.kind_id: None}}
