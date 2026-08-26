import asyncio
import datetime
import uuid
from typing import cast

import pytest
from pytest_mock import MockerFixture

from ffun.audit import domain as audit_domain
from ffun.audit.entities import AuditEntityKind
from ffun.core.postgresql import ExecuteType, execute, transaction
from ffun.core.tests.helpers import (
    TableSizeDelta,
    TableSizeNotChanged,
    assert_logs_has_business_event,
    assert_logs_has_no_business_event,
    capture_logs,
)
from ffun.domain.datetime_intervals import LIFETIME_INTERVAL_END_MARKER
from ffun.domain.domain import new_user_id
from ffun.domain.entities import BenefitTransactionId, SerializedId, UserId
from ffun.entitlements import domain
from ffun.entitlements import entities as entitlement_entities
from ffun.entitlements import errors, operations
from ffun.entitlements.entities import (
    EntitlementGuarantee,
    EntitlementKindId,
    EntitlementSourceId,
    MergePolicy,
    SourceEntitlement,
)
from ffun.entitlements.tests.helpers import (
    _ACTOR_ID,
    _ACTOR_KIND,
    _REVOKING_TRANSACTION_ID,
    _grant,
    _revoke,
    clear_effective_intervals,
)
from ffun.entitlements.tests.make import make_effective_entitlement_interval, make_source_entitlement
from ffun.locks.entities import LockKind
from ffun.one_time_purchases.domain import new_purchase_id
from ffun.subscriptions.domain import new_subscription_id

_DAY_TOKENS = EntitlementKindId.day_tokens
_MONTH_TOKENS = EntitlementKindId.month_tokens
_LIFETIME_TOKENS = EntitlementKindId.lifetime_tokens
_SOURCE_ID = EntitlementSourceId("test")
_GRANT_TRANSACTION_ID = BenefitTransactionId(uuid.UUID(int=1))


class TestEmptyBusinessEventCallback:
    def test_emits_no_business_events(self) -> None:
        with capture_logs() as logs:
            domain._empty_business_event_callback()

        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")


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


class TestGuaranteeKindId:
    def test_returns_kind_id(self) -> None:
        guarantee = EntitlementGuarantee(kind_id=_MONTH_TOKENS, value=10)

        assert domain._guarantee_kind_id(guarantee) == _MONTH_TOKENS


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

    def test_result_must_fit_persistence_bounds(self) -> None:
        with pytest.raises(errors.InvalidMergeValues, match="persistence-safe bounds"):
            domain.merge_values(
                MergePolicy.sum,
                [entitlement_entities.MAX_ENTITLEMENT_VALUE, 1],
            )


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
            source_id=EntitlementSourceId("first"),
            value=10,
            starts_at=now - datetime.timedelta(days=2),
            expires_at=now + datetime.timedelta(days=2),
        )
        second = make_source_entitlement(
            user_id=user_id,
            source_id=EntitlementSourceId("second"),
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

    def test_revoked_entitlement_is_excluded_regardless_of_revocation_time(self) -> None:
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

        assert intervals == []

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
        second = first.replace(grant_transaction_id=BenefitTransactionId(uuid.uuid4()), value=20)

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
    async def test_rebuilds_effective_state_and_records_complete_audit(self) -> None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)
        source_state = make_source_entitlement(
            grant_transaction_id=_GRANT_TRANSACTION_ID,
            subscription_id=new_subscription_id(),
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
        assert records[-1].attributes == {
            "source_id": source_state.source_id,
            "subscription_id": str(source_state.subscription_id),
            "one_time_purchase_id": None,
            "grant_transaction_id": str(source_state.grant_transaction_id),
            "revoked_by_transaction_id": None,
            "kind_id": source_state.kind_id.value,
            "previous_source_state": None,
            "new_source_state": cast(dict[str, object], source_state.model_dump(mode="json")),
            "previous_effective_intervals": [],
            "new_effective_intervals": [
                cast(dict[str, object], interval.model_dump(mode="json")) for interval in outcome.effective_intervals
            ],
        }


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
                source_state.source_id,
                source_state.grant_transaction_id,
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
        await _grant(source_state, evaluation_time=evaluation_time)

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
        await _grant(source_state, evaluation_time=evaluation_time)

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
        now = datetime.datetime.now(tz=datetime.UTC)

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
                        source_id=source_state.source_id,
                        grant_transaction_id=source_state.grant_transaction_id,
                        revoked_by_transaction_id=_REVOKING_TRANSACTION_ID,
                        user_id=source_state.user_id,
                        evaluation_time=now,
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
        await _grant(source_state, evaluation_time=evaluation_time)

        async with transaction() as transaction_execute:
            outcome = await domain._apply_source_revocation(
                transaction_execute,
                kind=domain.get_entitlement_kind(source_state.kind_id),
                source_id=source_state.source_id,
                grant_transaction_id=source_state.grant_transaction_id,
                revoked_by_transaction_id=_REVOKING_TRANSACTION_ID,
                user_id=source_state.user_id,
                evaluation_time=evaluation_time,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert outcome.changed
        assert outcome.effective_state == (False, None)
        assert outcome.effective_intervals == []
        assert outcome.source_state == source_state.replace(
            revoked_at=evaluation_time,
            revoked_by_transaction_id=_REVOKING_TRANSACTION_ID,
        )

    @pytest.mark.asyncio
    async def test_already_revoked_source_is_unchanged(self) -> None:
        source_state = make_source_entitlement()
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)
        await _grant(source_state, evaluation_time=evaluation_time)
        first, _ = await _revoke(
            source_state,
            evaluation_time=evaluation_time,
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
                    source_id=source_state.source_id,
                    grant_transaction_id=source_state.grant_transaction_id,
                    revoked_by_transaction_id=BenefitTransactionId(uuid.uuid4()),
                    user_id=source_state.user_id,
                    evaluation_time=evaluation_time + datetime.timedelta(days=1),
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

        assert not outcome.changed
        assert outcome.source_state == first.source_state


class TestEmitSourceChangeEvents:
    @pytest.mark.parametrize(
        ("revoked_at", "granted"),
        [(None, True), (datetime.datetime.now(tz=datetime.UTC), False)],
    )
    def test_emits_complete_source_and_effective_events(
        self,
        revoked_at: datetime.datetime | None,
        granted: bool,
    ) -> None:
        source_state = make_source_entitlement(
            grant_transaction_id=_GRANT_TRANSACTION_ID,
            subscription_id=new_subscription_id(),
            revoked_at=revoked_at,
            revoked_by_transaction_id=_REVOKING_TRANSACTION_ID if revoked_at is not None else None,
        )
        interval = make_effective_entitlement_interval(
            user_id=source_state.user_id,
            kind_id=source_state.kind_id,
            value=source_state.value,
            starts_at=source_state.starts_at,
            expires_at=source_state.expires_at,
        )
        outcome = entitlement_entities.SourceEntitlementChange(
            changed=True,
            effective_state=(granted, source_state.value if granted else None),
            effective_intervals=[interval] if granted else [],
            source_state=source_state,
        )

        with capture_logs() as logs:
            domain._emit_source_change_events(outcome)

        assert_logs_has_business_event(
            logs,
            "source_entitlement_changed",
            user_id=source_state.user_id,
            source_id=source_state.source_id,
            subscription_id=str(source_state.subscription_id),
            one_time_purchase_id=None,
            grant_transaction_id=str(source_state.grant_transaction_id),
            revoked_by_transaction_id=(
                str(source_state.revoked_by_transaction_id)
                if source_state.revoked_by_transaction_id is not None
                else None
            ),
            kind_id=source_state.kind_id.value,
            granted=granted,
            value=source_state.value,
            starts_at=source_state.starts_at.isoformat(),
            expires_at=source_state.expires_at.isoformat(),
            revoked_at=revoked_at.isoformat() if revoked_at is not None else None,
        )
        assert_logs_has_business_event(
            logs,
            "entitlement_changed",
            user_id=source_state.user_id,
            kind_id=source_state.kind_id.value,
            granted=granted,
            value=source_state.value if granted else None,
        )


class TestGrantSourceEntitlement:
    @pytest.mark.asyncio
    async def test_invalid_grant_does_not_change_persistence(self) -> None:
        now = datetime.datetime.now(tz=datetime.UTC)
        source_entitlement = make_source_entitlement(
            kind_id=_LIFETIME_TOKENS,
            starts_at=now,
            expires_at=now + datetime.timedelta(days=1),
        )

        async with (
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            with pytest.raises(errors.InvalidSourceEntitlement):
                async with transaction() as transaction_execute:
                    await domain.grant_source_entitlement(
                        transaction_execute,
                        source_entitlement,
                        evaluation_time=now,
                        actor_kind=_ACTOR_KIND,
                        actor_id=_ACTOR_ID,
                    )

    @pytest.mark.asyncio
    async def test_locks_user_and_kind(self, mocker: MockerFixture) -> None:
        source_entitlement = make_source_entitlement()
        lock_factory = mocker.patch.object(domain, "Lock")

        await _grant(source_entitlement, emit_event=False)

        lock_factory.assert_called_once_with(
            cast(object, mocker.ANY),
            LockKind("entitlements_user_kind"),
            source_entitlement.user_id,
            source_entitlement.kind_id,
        )

    @pytest.mark.asyncio
    async def test_same_user_and_kind_cannot_load_while_first_grant_holds_lock(
        self,
        mocker: MockerFixture,
    ) -> None:
        user_id = new_user_id()
        first = make_source_entitlement(user_id=user_id)
        second = make_source_entitlement(user_id=user_id)
        first_load_entered = asyncio.Event()
        release_first_load = asyncio.Event()
        second_grant_attempting = asyncio.Event()
        second_load_entered = asyncio.Event()
        original_load_source_entitlement = operations.load_source_entitlement

        async def tracked_load_source_entitlement(
            transaction_execute: ExecuteType,
            loaded_user_id: UserId,
            kind_id: EntitlementKindId,
            source_id: EntitlementSourceId,
            grant_transaction_id: BenefitTransactionId,
        ) -> SourceEntitlement | None:
            if grant_transaction_id == first.grant_transaction_id:
                first_load_entered.set()
                await release_first_load.wait()
            elif grant_transaction_id == second.grant_transaction_id:
                second_load_entered.set()

            return await original_load_source_entitlement(
                transaction_execute,
                loaded_user_id,
                kind_id,
                source_id,
                grant_transaction_id,
            )

        async def grant_second() -> entitlement_entities.SourceEntitlementChange:
            second_grant_attempting.set()
            outcome, _ = await _grant(second, emit_event=False)
            return outcome

        mocker.patch.object(
            operations,
            "load_source_entitlement",
            side_effect=tracked_load_source_entitlement,
        )

        first_grant = asyncio.create_task(_grant(first, emit_event=False))
        await first_load_entered.wait()
        second_grant = asyncio.create_task(grant_second())
        await second_grant_attempting.wait()

        try:
            with pytest.raises(TimeoutError):
                async with asyncio.timeout(0.05):
                    await second_load_entered.wait()
        finally:
            release_first_load.set()
            (first_outcome, _), second_outcome = await asyncio.gather(first_grant, second_grant)

        assert second_load_entered.is_set()
        assert first_outcome.changed
        assert second_outcome.changed

    @pytest.mark.asyncio
    async def test_stores_grant_audit_and_returns_post_commit_events(self) -> None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)
        source_entitlement = make_source_entitlement(
            grant_transaction_id=_GRANT_TRANSACTION_ID,
            subscription_id=new_subscription_id(),
            starts_at=evaluation_time - datetime.timedelta(days=1),
            expires_at=evaluation_time + datetime.timedelta(days=1),
        )

        with capture_logs() as logs:
            async with (
                TableSizeDelta("en_source_entitlements", delta=1),
                TableSizeDelta("en_entitlements", delta=1),
                TableSizeDelta("a_records", delta=1),
            ):
                outcome, callback = await _grant(
                    source_entitlement,
                    evaluation_time=evaluation_time,
                    emit_event=False,
                )

            assert_logs_has_no_business_event(logs, "source_entitlement_changed")
            assert_logs_has_no_business_event(logs, "entitlement_changed")
            callback()

        assert outcome.changed
        assert outcome.effective_state == (True, source_entitlement.value)
        assert outcome.source_state == source_entitlement
        assert_logs_has_business_event(
            logs,
            "source_entitlement_changed",
            user_id=source_entitlement.user_id,
            grant_transaction_id=str(source_entitlement.grant_transaction_id),
            granted=True,
        )
        assert_logs_has_business_event(
            logs,
            "entitlement_changed",
            user_id=source_entitlement.user_id,
            granted=True,
            value=source_entitlement.value,
        )

    @pytest.mark.asyncio
    async def test_identical_grant_is_no_op(self) -> None:
        source_entitlement = make_source_entitlement()
        await _grant(source_entitlement)

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                outcome, callback = await _grant(source_entitlement, emit_event=False)
            callback()

        assert not outcome.changed
        assert outcome.source_state == source_entitlement
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_reusing_identity_with_different_immutable_fields_fails(self) -> None:
        source_entitlement = make_source_entitlement()
        await _grant(source_entitlement)

        async with (
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            with pytest.raises(errors.SourceEntitlementConflict):
                await _grant(source_entitlement.replace(value=20))

    @pytest.mark.asyncio
    async def test_future_grant_does_not_replace_current_grant(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        current = make_source_entitlement(
            user_id=user_id,
            value=10,
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=1),
        )
        await _grant(current, evaluation_time=now)
        future_start = now + datetime.timedelta(days=2)
        future = make_source_entitlement(
            user_id=user_id,
            value=20,
            starts_at=future_start,
            expires_at=future_start + datetime.timedelta(days=1),
        )

        outcome, _ = await _grant(future, evaluation_time=now)

        assert outcome.effective_state == (True, 10)
        assert [(interval.value, interval.starts_at) for interval in outcome.effective_intervals] == [
            (10, current.starts_at),
            (20, future_start),
        ]

    @pytest.mark.asyncio
    async def test_lifetime_transactions_sum(self) -> None:
        user_id = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        first = make_source_entitlement(
            user_id=user_id,
            kind_id=_LIFETIME_TOKENS,
            value=10,
            starts_at=starts_at,
            expires_at=LIFETIME_INTERVAL_END_MARKER,
        )
        second = make_source_entitlement(
            user_id=user_id,
            kind_id=_LIFETIME_TOKENS,
            value=20,
            starts_at=starts_at,
            expires_at=LIFETIME_INTERVAL_END_MARKER,
        )
        await _grant(first)

        outcome, _ = await _grant(second)

        assert outcome.effective_state == (True, 30)

    @pytest.mark.asyncio
    async def test_audit_failure_rolls_back_without_events(self, mocker: MockerFixture) -> None:
        source_entitlement = make_source_entitlement()
        mocker.patch.object(audit_domain, "record", side_effect=RuntimeError("audit failed"))

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(RuntimeError, match="audit failed"):
                    await _grant(source_entitlement)

        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")


class TestRevokeSourceEntitlement:
    @pytest.mark.asyncio
    async def test_locks_user_and_kind(self, mocker: MockerFixture) -> None:
        source_entitlement = make_source_entitlement()
        await _grant(source_entitlement)
        lock_factory = mocker.patch.object(domain, "Lock")

        await _revoke(source_entitlement, emit_event=False)

        lock_factory.assert_called_once_with(
            cast(object, mocker.ANY),
            LockKind("entitlements_user_kind"),
            source_entitlement.user_id,
            source_entitlement.kind_id,
        )

    @pytest.mark.asyncio
    async def test_missing_grant_fails_without_changes(self) -> None:
        source_entitlement = make_source_entitlement()

        async with (
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            with pytest.raises(errors.SourceEntitlementNotFound):
                await _revoke(source_entitlement)

    @pytest.mark.asyncio
    async def test_revokes_grant_and_records_complete_change(self) -> None:
        evaluation_time = datetime.datetime.now(tz=datetime.UTC)
        source_entitlement = make_source_entitlement(
            grant_transaction_id=_GRANT_TRANSACTION_ID,
            starts_at=evaluation_time - datetime.timedelta(days=1),
            expires_at=evaluation_time + datetime.timedelta(days=1),
        )
        await _grant(source_entitlement, evaluation_time=evaluation_time)

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeDelta("en_entitlements", delta=-1),
                TableSizeDelta("a_records", delta=1),
            ):
                outcome, callback = await _revoke(
                    source_entitlement,
                    evaluation_time=evaluation_time,
                    emit_event=False,
                )
            assert_logs_has_no_business_event(logs, "source_entitlement_changed")
            callback()

        expected = source_entitlement.replace(
            revoked_at=evaluation_time,
            revoked_by_transaction_id=_REVOKING_TRANSACTION_ID,
        )
        assert outcome.changed
        assert outcome.effective_state == (False, None)
        assert outcome.source_state == expected
        records = await audit_domain.load_records_for_subject(
            execute,
            subject_kind=AuditEntityKind.user,
            subject_id=SerializedId(str(source_entitlement.user_id)),
        )
        assert records[-1].attributes["previous_source_state"] == cast(
            dict[str, object], source_entitlement.model_dump(mode="json")
        )
        assert records[-1].attributes["new_source_state"] == cast(dict[str, object], expected.model_dump(mode="json"))
        assert records[-1].attributes["revoked_by_transaction_id"] == str(_REVOKING_TRANSACTION_ID)
        assert_logs_has_business_event(
            logs,
            "source_entitlement_changed",
            user_id=source_entitlement.user_id,
            grant_transaction_id=str(_GRANT_TRANSACTION_ID),
            revoked_by_transaction_id=str(_REVOKING_TRANSACTION_ID),
            granted=False,
        )

    @pytest.mark.asyncio
    async def test_repeated_revocation_is_no_op_and_preserves_causality(self) -> None:
        source_entitlement = make_source_entitlement()
        now = datetime.datetime.now(tz=datetime.UTC)
        await _grant(source_entitlement, evaluation_time=now)
        first, _ = await _revoke(source_entitlement, evaluation_time=now)

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                second, callback = await _revoke(
                    source_entitlement,
                    revoked_by_transaction_id=BenefitTransactionId(uuid.uuid4()),
                    evaluation_time=now + datetime.timedelta(days=1),
                    emit_event=False,
                )
            callback()

        assert not second.changed
        assert second.source_state == first.source_state
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")

    @pytest.mark.asyncio
    async def test_grant_retry_after_revocation_is_no_op(self) -> None:
        source_entitlement = make_source_entitlement()
        await _grant(source_entitlement)
        revoked, _ = await _revoke(source_entitlement)

        outcome, _ = await _grant(source_entitlement)

        assert not outcome.changed
        assert outcome.source_state == revoked.source_state

    @pytest.mark.asyncio
    async def test_revoking_one_transaction_preserves_other_grants(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        first = make_source_entitlement(
            user_id=user_id,
            value=10,
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=1),
        )
        second = make_source_entitlement(
            user_id=user_id,
            value=20,
            starts_at=first.starts_at,
            expires_at=first.expires_at,
        )
        await _grant(first, evaluation_time=now)
        await _grant(second, evaluation_time=now)

        outcome, _ = await _revoke(second, evaluation_time=now)

        assert outcome.effective_state == (True, 10)
        sources = await operations.load_source_entitlements(execute, user_id, _DAY_TOKENS)
        assert {source.grant_transaction_id: source.granted for source in sources} == {
            first.grant_transaction_id: True,
            second.grant_transaction_id: False,
        }

    @pytest.mark.asyncio
    async def test_audit_failure_rolls_back_revocation_without_events(self, mocker: MockerFixture) -> None:
        source_entitlement = make_source_entitlement()
        await _grant(source_entitlement)
        mocker.patch.object(audit_domain, "record", side_effect=RuntimeError("audit failed"))

        with capture_logs() as logs:
            async with (
                TableSizeNotChanged("en_source_entitlements"),
                TableSizeNotChanged("en_entitlements"),
                TableSizeNotChanged("a_records"),
            ):
                with pytest.raises(RuntimeError, match="audit failed"):
                    await _revoke(source_entitlement)

        stored = await operations.load_source_entitlement(
            execute,
            source_entitlement.user_id,
            source_entitlement.kind_id,
            source_entitlement.source_id,
            source_entitlement.grant_transaction_id,
        )
        assert stored == source_entitlement
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")


class TestGrantSourceEntitlements:
    @pytest.mark.asyncio
    async def test_empty_guarantees_return_empty_results(self) -> None:
        async with transaction() as transaction_execute:
            outcomes, callbacks = await domain.grant_source_entitlements(
                transaction_execute,
                source_id=_SOURCE_ID,
                grant_transaction_id=_GRANT_TRANSACTION_ID,
                user_id=new_user_id(),
                subscription_id=None,
                one_time_purchase_id=None,
                guarantees=[],
                starts_at=datetime.datetime.now(tz=datetime.UTC),
                expires_at=datetime.datetime.now(tz=datetime.UTC) + datetime.timedelta(days=1),
                evaluation_time=datetime.datetime.now(tz=datetime.UTC),
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert outcomes == []
        assert callbacks == []

    @pytest.mark.asyncio
    async def test_grants_sorted_guarantees_with_supplied_expiration_and_subscription(self) -> None:
        user_id = new_user_id()
        subscription_id = new_subscription_id()
        now = datetime.datetime.now(tz=datetime.UTC)

        with capture_logs() as logs:
            async with transaction() as transaction_execute:
                outcomes, callbacks = await domain.grant_source_entitlements(
                    transaction_execute,
                    source_id=_SOURCE_ID,
                    grant_transaction_id=_GRANT_TRANSACTION_ID,
                    user_id=user_id,
                    subscription_id=subscription_id,
                    one_time_purchase_id=None,
                    guarantees=[
                        EntitlementGuarantee(kind_id=_MONTH_TOKENS, value=30),
                        EntitlementGuarantee(kind_id=_DAY_TOKENS, value=10),
                    ],
                    starts_at=now,
                    expires_at=now + datetime.timedelta(days=1),
                    evaluation_time=now,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

            assert_logs_has_no_business_event(logs, "source_entitlement_changed")
            for callback in callbacks:
                callback()

        assert [outcome.source_state.kind_id for outcome in outcomes] == [_DAY_TOKENS, _MONTH_TOKENS]
        assert all(outcome.source_state.expires_at == now + datetime.timedelta(days=1) for outcome in outcomes)
        assert all(outcome.source_state.subscription_id == subscription_id for outcome in outcomes)
        assert all(outcome.source_state.grant_transaction_id == _GRANT_TRANSACTION_ID for outcome in outcomes)
        assert sum(record.get("event") == "source_entitlement_changed" for record in logs) == 2
        assert sum(record.get("event") == "entitlement_changed" for record in logs) == 2

    @pytest.mark.asyncio
    async def test_grants_one_time_purchase_owned_guarantee_with_audit_and_events(self) -> None:
        user_id = new_user_id()
        one_time_purchase_id = new_purchase_id()
        now = datetime.datetime.now(tz=datetime.UTC)

        with capture_logs() as logs:
            async with transaction() as transaction_execute:
                outcomes, callbacks = await domain.grant_source_entitlements(
                    transaction_execute,
                    source_id=_SOURCE_ID,
                    grant_transaction_id=_GRANT_TRANSACTION_ID,
                    user_id=user_id,
                    subscription_id=None,
                    one_time_purchase_id=one_time_purchase_id,
                    guarantees=[EntitlementGuarantee(kind_id=_LIFETIME_TOKENS, value=30)],
                    starts_at=now,
                    expires_at=LIFETIME_INTERVAL_END_MARKER,
                    evaluation_time=now,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

            assert_logs_has_no_business_event(logs, "source_entitlement_changed")
            for callback in callbacks:
                callback()

        assert len(outcomes) == 1
        assert outcomes[0].source_state.subscription_id is None
        assert outcomes[0].source_state.one_time_purchase_id == one_time_purchase_id
        records = await audit_domain.load_records_for_subject(
            execute,
            subject_kind=AuditEntityKind.user,
            subject_id=SerializedId(str(user_id)),
        )
        assert records[-1].attributes["subscription_id"] is None
        assert records[-1].attributes["one_time_purchase_id"] == str(one_time_purchase_id)
        assert_logs_has_business_event(
            logs,
            "source_entitlement_changed",
            user_id=user_id,
            subscription_id=None,
            one_time_purchase_id=str(one_time_purchase_id),
            granted=True,
        )

    @pytest.mark.asyncio
    async def test_invalid_interval_is_module_error_and_rolls_back(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)

        async with (
            TableSizeNotChanged("en_source_entitlements"),
            TableSizeNotChanged("en_entitlements"),
            TableSizeNotChanged("a_records"),
        ):
            with pytest.raises(errors.InvalidSourceEntitlement):
                async with transaction() as transaction_execute:
                    await domain.grant_source_entitlements(
                        transaction_execute,
                        source_id=_SOURCE_ID,
                        grant_transaction_id=_GRANT_TRANSACTION_ID,
                        user_id=user_id,
                        subscription_id=None,
                        one_time_purchase_id=None,
                        guarantees=[EntitlementGuarantee(kind_id=_DAY_TOKENS, value=10)],
                        starts_at=now,
                        expires_at=now,
                        evaluation_time=now,
                        actor_kind=_ACTOR_KIND,
                        actor_id=_ACTOR_ID,
                    )


class TestRevokeSubscriptionEntitlements:
    @pytest.mark.asyncio
    async def test_missing_subscription_grants_return_empty_results(self) -> None:
        async with transaction() as transaction_execute:
            outcomes, callbacks = await domain.revoke_subscription_entitlements(
                transaction_execute,
                subscription_id=new_subscription_id(),
                revoked_by_transaction_id=_REVOKING_TRANSACTION_ID,
                evaluation_time=datetime.datetime.now(tz=datetime.UTC),
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert outcomes == []
        assert callbacks == []

    @pytest.mark.asyncio
    async def test_revokes_expired_and_ignores_already_revoked_subscription_grants(self) -> None:
        user_id = new_user_id()
        subscription_id = new_subscription_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        expired = make_source_entitlement(
            user_id=user_id,
            subscription_id=subscription_id,
            grant_transaction_id=BenefitTransactionId(uuid.UUID(int=5)),
            starts_at=now - datetime.timedelta(days=2),
            expires_at=now,
        )
        revoked = make_source_entitlement(
            user_id=user_id,
            subscription_id=subscription_id,
            grant_transaction_id=BenefitTransactionId(uuid.UUID(int=6)),
            starts_at=now - datetime.timedelta(days=2),
            expires_at=now + datetime.timedelta(days=1),
            revoked_at=now - datetime.timedelta(days=1),
        )
        await operations.insert_source_entitlement(execute, expired)
        await operations.insert_source_entitlement(execute, revoked)

        async with transaction() as transaction_execute:
            outcomes, callbacks = await domain.revoke_subscription_entitlements(
                transaction_execute,
                subscription_id=subscription_id,
                revoked_by_transaction_id=_REVOKING_TRANSACTION_ID,
                evaluation_time=now,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        revoked_expired = expired.replace(
            revoked_at=now,
            revoked_by_transaction_id=_REVOKING_TRANSACTION_ID,
        )
        assert [outcome.source_state for outcome in outcomes] == [revoked_expired]
        assert len(callbacks) == 1
        assert await operations.load_source_entitlements_for_subscription(execute, subscription_id) == [
            revoked_expired,
            revoked,
        ]

    @pytest.mark.asyncio
    async def test_revokes_active_and_future_grants_linked_to_subscription(self) -> None:
        user_id = new_user_id()
        subscription_id = new_subscription_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        future_transaction_id = BenefitTransactionId(uuid.UUID(int=3))
        async with transaction() as transaction_execute:
            granted, grant_callbacks = await domain.grant_source_entitlements(
                transaction_execute,
                source_id=_SOURCE_ID,
                grant_transaction_id=_GRANT_TRANSACTION_ID,
                user_id=user_id,
                subscription_id=subscription_id,
                one_time_purchase_id=None,
                guarantees=[
                    EntitlementGuarantee(kind_id=_DAY_TOKENS, value=10),
                    EntitlementGuarantee(kind_id=_MONTH_TOKENS, value=20),
                ],
                starts_at=now - datetime.timedelta(days=1),
                expires_at=now + datetime.timedelta(days=1),
                evaluation_time=now,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )
            future_granted, future_grant_callbacks = await domain.grant_source_entitlements(
                transaction_execute,
                source_id=_SOURCE_ID,
                grant_transaction_id=future_transaction_id,
                user_id=user_id,
                subscription_id=subscription_id,
                one_time_purchase_id=None,
                guarantees=[EntitlementGuarantee(kind_id=_DAY_TOKENS, value=30)],
                starts_at=now + datetime.timedelta(days=1),
                expires_at=now + datetime.timedelta(days=2),
                evaluation_time=now,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        for callback in grant_callbacks + future_grant_callbacks:
            callback()

        async with transaction() as transaction_execute:
            outcomes, callbacks = await domain.revoke_subscription_entitlements(
                transaction_execute,
                subscription_id=subscription_id,
                revoked_by_transaction_id=_REVOKING_TRANSACTION_ID,
                evaluation_time=now,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        for callback in callbacks:
            callback()

        assert [(outcome.source_state.kind_id, outcome.source_state.grant_transaction_id) for outcome in outcomes] == [
            (_DAY_TOKENS, _GRANT_TRANSACTION_ID),
            (_DAY_TOKENS, future_transaction_id),
            (_MONTH_TOKENS, _GRANT_TRANSACTION_ID),
        ]
        assert all(not outcome.source_state.granted for outcome in outcomes)
        assert all(outcome.source_state.revoked_by_transaction_id == _REVOKING_TRANSACTION_ID for outcome in outcomes)
        assert len(callbacks) == len(granted) + len(future_granted)


class TestRevokeOneTimePurchaseEntitlements:
    @pytest.mark.asyncio
    async def test_missing_purchase_grants_return_empty_results(self) -> None:
        async with transaction() as transaction_execute:
            outcomes, callbacks = await domain.revoke_one_time_purchase_entitlements(
                transaction_execute,
                one_time_purchase_id=new_purchase_id(),
                revoked_by_transaction_id=_REVOKING_TRANSACTION_ID,
                evaluation_time=datetime.datetime.now(tz=datetime.UTC),
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        assert outcomes == []
        assert callbacks == []

    @pytest.mark.asyncio
    async def test_revokes_expired_and_ignores_already_revoked_purchase_grants(self) -> None:
        user_id = new_user_id()
        one_time_purchase_id = new_purchase_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        expired = make_source_entitlement(
            user_id=user_id,
            one_time_purchase_id=one_time_purchase_id,
            grant_transaction_id=BenefitTransactionId(uuid.UUID(int=5)),
            starts_at=now - datetime.timedelta(days=2),
            expires_at=now,
        )
        revoked = make_source_entitlement(
            user_id=user_id,
            one_time_purchase_id=one_time_purchase_id,
            grant_transaction_id=BenefitTransactionId(uuid.UUID(int=6)),
            starts_at=now - datetime.timedelta(days=2),
            expires_at=now + datetime.timedelta(days=1),
            revoked_at=now - datetime.timedelta(days=1),
        )
        await operations.insert_source_entitlement(execute, expired)
        await operations.insert_source_entitlement(execute, revoked)

        async with transaction() as transaction_execute:
            outcomes, callbacks = await domain.revoke_one_time_purchase_entitlements(
                transaction_execute,
                one_time_purchase_id=one_time_purchase_id,
                revoked_by_transaction_id=_REVOKING_TRANSACTION_ID,
                evaluation_time=now,
                actor_kind=_ACTOR_KIND,
                actor_id=_ACTOR_ID,
            )

        revoked_expired = expired.replace(
            revoked_at=now,
            revoked_by_transaction_id=_REVOKING_TRANSACTION_ID,
        )
        assert [outcome.source_state for outcome in outcomes] == [revoked_expired]
        assert len(callbacks) == 1
        assert await operations.load_source_entitlements_for_one_time_purchase(execute, one_time_purchase_id) == [
            revoked_expired,
            revoked,
        ]

    @pytest.mark.asyncio
    async def test_revokes_purchase_grants_and_rebuilds_timeline_without_other_purchase(self) -> None:
        user_id = new_user_id()
        one_time_purchase_id = new_purchase_id()
        other_purchase_id = new_purchase_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        future_transaction_id = BenefitTransactionId(uuid.UUID(int=3))
        other_transaction_id = BenefitTransactionId(uuid.UUID(int=4))

        grants = (
            (_GRANT_TRANSACTION_ID, one_time_purchase_id, 100, -1),
            (future_transaction_id, one_time_purchase_id, 50, 1),
            (other_transaction_id, other_purchase_id, 250, -1),
        )
        grant_callbacks = []
        async with transaction() as transaction_execute:
            for transaction_id, purchase_id, value, starts_in_days in grants:
                _, callbacks = await domain.grant_source_entitlements(
                    transaction_execute,
                    source_id=_SOURCE_ID,
                    grant_transaction_id=transaction_id,
                    user_id=user_id,
                    subscription_id=None,
                    one_time_purchase_id=purchase_id,
                    guarantees=[EntitlementGuarantee(kind_id=_LIFETIME_TOKENS, value=value)],
                    starts_at=now + datetime.timedelta(days=starts_in_days),
                    expires_at=LIFETIME_INTERVAL_END_MARKER,
                    evaluation_time=now,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )
                grant_callbacks.extend(callbacks)

        for callback in grant_callbacks:
            callback()

        with capture_logs() as logs:
            async with transaction() as transaction_execute:
                outcomes, callbacks = await domain.revoke_one_time_purchase_entitlements(
                    transaction_execute,
                    one_time_purchase_id=one_time_purchase_id,
                    revoked_by_transaction_id=_REVOKING_TRANSACTION_ID,
                    evaluation_time=now,
                    actor_kind=_ACTOR_KIND,
                    actor_id=_ACTOR_ID,
                )

            assert_logs_has_no_business_event(logs, "source_entitlement_changed")
            for callback in callbacks:
                callback()

        assert [outcome.source_state.grant_transaction_id for outcome in outcomes] == [
            _GRANT_TRANSACTION_ID,
            future_transaction_id,
        ]
        assert all(not outcome.source_state.granted for outcome in outcomes)
        assert all(outcome.source_state.one_time_purchase_id == one_time_purchase_id for outcome in outcomes)
        assert len(callbacks) == 2
        effective = (await domain.get_entitlements([user_id], [_LIFETIME_TOKENS]))[user_id][_LIFETIME_TOKENS]
        assert effective is not None
        assert effective.value == 250

        source_entitlements = await operations.load_source_entitlements(execute, user_id, _LIFETIME_TOKENS)
        assert {source.grant_transaction_id: source.granted for source in source_entitlements} == {
            _GRANT_TRANSACTION_ID: False,
            future_transaction_id: False,
            other_transaction_id: True,
        }
        records = await audit_domain.load_records_for_subject(
            execute,
            subject_kind=AuditEntityKind.user,
            subject_id=SerializedId(str(user_id)),
        )
        assert [record.attributes["one_time_purchase_id"] for record in records[-2:]] == [
            str(one_time_purchase_id),
            str(one_time_purchase_id),
        ]
        assert sum(record.get("event") == "source_entitlement_changed" for record in logs) == 2
        assert sum(record.get("event") == "entitlement_changed" for record in logs) == 2
        assert_logs_has_business_event(
            logs,
            "source_entitlement_changed",
            user_id=user_id,
            one_time_purchase_id=str(one_time_purchase_id),
            revoked_by_transaction_id=str(_REVOKING_TRANSACTION_ID),
            granted=False,
        )


class TestGetEntitlements:
    @pytest.mark.asyncio
    async def test_returns_every_user_and_selected_kind(self) -> None:
        entitled_user = new_user_id()
        other_user = new_user_id()
        starts_at = datetime.datetime.now(tz=datetime.UTC) - datetime.timedelta(days=1)
        expires_at = starts_at + datetime.timedelta(days=2)
        source_entitlement = make_source_entitlement(
            user_id=entitled_user,
            starts_at=starts_at,
            expires_at=expires_at,
        )
        await _grant(source_entitlement)

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
    async def test_query_does_not_remove_expired_rows_or_emit_events(self) -> None:
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

        with capture_logs() as logs:
            async with TableSizeNotChanged("en_entitlements"):
                listed = await domain.get_entitlements([interval.user_id], [interval.kind_id])

        assert listed == {interval.user_id: {interval.kind_id: None}}
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
    async def test_deletes_expired_effective_rows_only_without_events(self) -> None:
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

        with capture_logs() as logs:
            async with TableSizeNotChanged("en_source_entitlements"):
                async with TableSizeDelta("en_entitlements", delta=-1):
                    deleted = await domain.cleanup_expired_entitlements()

        assert deleted == 1
        assert_logs_has_no_business_event(logs, "source_entitlement_changed")
        assert_logs_has_no_business_event(logs, "entitlement_changed")
