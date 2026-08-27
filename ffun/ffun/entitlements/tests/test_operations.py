import asyncio
import datetime
import uuid
from typing import cast

import pytest
from psycopg.errors import CheckViolation, UniqueViolation
from pydantic import ValidationError

from ffun.core.postgresql import execute, transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.domain.domain import new_user_id
from ffun.domain.entities import BenefitTransactionId, UserId
from ffun.entitlements import errors, operations
from ffun.entitlements.entities import EntitlementKindId
from ffun.entitlements.tests.helpers import load_effective_interval_timestamps, load_source_entitlement_timestamps
from ffun.entitlements.tests.make import make_effective_entitlement_interval, make_source_entitlement
from ffun.one_time_purchases.domain import new_purchase_id
from ffun.subscriptions.domain import new_subscription_id


def _transaction_id(value: int) -> BenefitTransactionId:
    return BenefitTransactionId(uuid.UUID(int=value))


def _ordered_transaction_ids(count: int) -> tuple[BenefitTransactionId, ...]:
    base = uuid.uuid4().int & ~0xFFFF
    return tuple(BenefitTransactionId(uuid.UUID(int=base + offset)) for offset in range(1, count + 1))


class TestRowToSourceEntitlement:
    def test_converts_row_and_removes_persistence_timestamps(self) -> None:
        entitlement = make_source_entitlement()
        now = datetime.datetime.now(tz=datetime.UTC)
        row = cast(dict[str, object], entitlement.model_dump())
        row.update({"created_at": now, "updated_at": now})

        assert operations.row_to_source_entitlement(row) == entitlement

    def test_invalid_row_raises_module_error(self) -> None:
        with pytest.raises(errors.InvalidStoredEntitlement) as exception_info:
            operations.row_to_source_entitlement({})

        assert "entity_kind=source_entitlement" in str(exception_info.value)
        assert isinstance(exception_info.value.__cause__, ValidationError)


class TestRowToEffectiveInterval:
    def test_converts_row(self) -> None:
        interval = make_effective_entitlement_interval()

        assert operations.row_to_effective_interval(cast(dict[str, object], interval.model_dump())) == interval

    def test_invalid_row_raises_module_error(self) -> None:
        with pytest.raises(errors.InvalidStoredEntitlement) as exception_info:
            operations.row_to_effective_interval({})

        assert "entity_kind=effective_entitlement_interval" in str(exception_info.value)
        assert isinstance(exception_info.value.__cause__, ValidationError)


class TestLoadSourceEntitlement:
    @pytest.mark.asyncio
    async def test_missing(self) -> None:
        loaded = await operations.load_source_entitlement(
            execute,
            new_user_id(),
            EntitlementKindId.day_tokens,
            BenefitTransactionId(uuid.uuid4()),
        )

        assert loaded is None

    @pytest.mark.asyncio
    async def test_identity_includes_grant_transaction(self) -> None:
        entitlement = make_source_entitlement()
        await operations.insert_source_entitlement(execute, entitlement)

        assert (
            await operations.load_source_entitlement(
                execute,
                entitlement.user_id,
                entitlement.kind_id,
                entitlement.grant_transaction_id,
            )
            == entitlement
        )
        assert (
            await operations.load_source_entitlement(
                execute,
                entitlement.user_id,
                entitlement.kind_id,
                BenefitTransactionId(uuid.uuid4()),
            )
            is None
        )


class TestInsertSourceEntitlement:
    @pytest.mark.asyncio
    async def test_inserts_complete_immutable_grant(self) -> None:
        entitlement = make_source_entitlement(subscription_id=new_subscription_id())

        async with TableSizeDelta("en_source_entitlements", delta=1):
            await operations.insert_source_entitlement(execute, entitlement)

        loaded = await operations.load_source_entitlement(
            execute,
            entitlement.user_id,
            entitlement.kind_id,
            entitlement.grant_transaction_id,
        )
        assert loaded == entitlement
        created_at, updated_at = await load_source_entitlement_timestamps(entitlement)
        assert created_at == updated_at

    @pytest.mark.asyncio
    async def test_inserts_one_time_purchase_owner(self) -> None:
        entitlement = make_source_entitlement(one_time_purchase_id=new_purchase_id())

        async with TableSizeDelta("en_source_entitlements", delta=1):
            await operations.insert_source_entitlement(execute, entitlement)

        assert (
            await operations.load_source_entitlement(
                execute,
                entitlement.user_id,
                entitlement.kind_id,
                entitlement.grant_transaction_id,
            )
            == entitlement
        )

    @pytest.mark.asyncio
    async def test_rejects_multiple_purchased_state_owners(self) -> None:
        entitlement = make_source_entitlement(subscription_id=new_subscription_id())
        arguments = cast(dict[str, object], entitlement.model_dump())
        arguments["one_time_purchase_id"] = new_purchase_id()
        check_violation = cast(type[Exception], CheckViolation)

        # Developer-approved direct SQL is required because valid entities reject multiple owners before persistence.
        async with TableSizeNotChanged("en_source_entitlements"):
            with pytest.raises(check_violation):
                await execute(
                    """
                    INSERT INTO en_source_entitlements (
                        grant_transaction_id,
                        user_id,
                        subscription_id,
                        one_time_purchase_id,
                        kind_id,
                        value,
                        starts_at,
                        expires_at,
                        revoked_at,
                        revoked_by_transaction_id
                    )
                    VALUES (
                        %(grant_transaction_id)s,
                        %(user_id)s,
                        %(subscription_id)s,
                        %(one_time_purchase_id)s,
                        %(kind_id)s,
                        %(value)s,
                        %(starts_at)s,
                        %(expires_at)s,
                        %(revoked_at)s,
                        %(revoked_by_transaction_id)s
                    )
                    """,
                    arguments,
                )

    @pytest.mark.asyncio
    async def test_inserts_multiple_grant_transactions(self) -> None:
        first_transaction_id, second_transaction_id = _ordered_transaction_ids(2)
        first = make_source_entitlement(grant_transaction_id=first_transaction_id)
        second = first.replace(grant_transaction_id=second_transaction_id, value=20)

        async with TableSizeDelta("en_source_entitlements", delta=2):
            await operations.insert_source_entitlement(execute, first)
            await operations.insert_source_entitlement(execute, second)

        assert await operations.load_source_entitlements(execute, first.user_id, first.kind_id) == [first, second]

    @pytest.mark.asyncio
    async def test_conflicting_identity_fails(self) -> None:
        entitlement = make_source_entitlement()
        await operations.insert_source_entitlement(execute, entitlement)
        conflicting = entitlement.replace(value=entitlement.value + 1)
        unique_violation = cast(type[Exception], UniqueViolation)

        async with TableSizeNotChanged("en_source_entitlements"):
            with pytest.raises(errors.SourceEntitlementConflict) as exception_info:
                await operations.insert_source_entitlement(execute, conflicting)

        assert isinstance(exception_info.value.__cause__, unique_violation)
        assert (
            await operations.load_source_entitlement(
                execute,
                entitlement.user_id,
                entitlement.kind_id,
                entitlement.grant_transaction_id,
            )
            == entitlement
        )


class TestRevokeSourceEntitlement:
    @pytest.mark.asyncio
    async def test_missing_source_raises_invalid_stored_entitlement(self) -> None:
        entitlement = make_source_entitlement()

        async with TableSizeNotChanged("en_source_entitlements"):
            with pytest.raises(errors.InvalidStoredEntitlement) as exception_info:
                await operations.revoke_source_entitlement(
                    execute,
                    entitlement,
                    revoked_at=datetime.datetime.now(tz=datetime.UTC),
                    revoked_by_transaction_id=_transaction_id(10),
                )

        assert "reason=Expected a source entitlement to exist" in str(exception_info.value)

    @pytest.mark.asyncio
    async def test_sets_revocation_causality_and_updated_timestamp(self) -> None:
        entitlement = make_source_entitlement()
        await operations.insert_source_entitlement(execute, entitlement)
        created_at, _ = await load_source_entitlement_timestamps(entitlement)
        await asyncio.sleep(0.001)
        revoked_at = datetime.datetime.now(tz=datetime.UTC)
        revoked_by_transaction_id = _transaction_id(10)

        async with TableSizeNotChanged("en_source_entitlements"):
            revoked = await operations.revoke_source_entitlement(
                execute,
                entitlement,
                revoked_at=revoked_at,
                revoked_by_transaction_id=revoked_by_transaction_id,
            )

        assert revoked == entitlement.replace(
            revoked_at=revoked_at,
            revoked_by_transaction_id=revoked_by_transaction_id,
        )
        assert (
            await operations.load_source_entitlement(
                execute,
                entitlement.user_id,
                entitlement.kind_id,
                entitlement.grant_transaction_id,
            )
            == revoked
        )
        revoked_created_at, revoked_updated_at = await load_source_entitlement_timestamps(entitlement)
        assert revoked_created_at == created_at
        assert revoked_updated_at > created_at

    @pytest.mark.asyncio
    async def test_existing_earlier_revocation_is_returned_and_preserved(self) -> None:
        entitlement = make_source_entitlement()
        await operations.insert_source_entitlement(execute, entitlement)
        original_revoked_at = datetime.datetime.now(tz=datetime.UTC)
        original_transaction_id = _transaction_id(10)
        revoked = await operations.revoke_source_entitlement(
            execute,
            entitlement,
            revoked_at=original_revoked_at,
            revoked_by_transaction_id=original_transaction_id,
        )
        timestamps = await load_source_entitlement_timestamps(entitlement)

        returned = await operations.revoke_source_entitlement(
            execute,
            revoked,
            revoked_at=original_revoked_at + datetime.timedelta(days=1),
            revoked_by_transaction_id=_transaction_id(11),
        )

        assert returned == revoked
        assert (
            await operations.load_source_entitlement(
                execute,
                entitlement.user_id,
                entitlement.kind_id,
                entitlement.grant_transaction_id,
            )
            == revoked
        )
        assert await load_source_entitlement_timestamps(entitlement) == timestamps

    @pytest.mark.asyncio
    async def test_earlier_retry_returns_existing_revocation_and_preserves_it(self) -> None:
        entitlement = make_source_entitlement()
        await operations.insert_source_entitlement(execute, entitlement)
        original_revoked_at = datetime.datetime.now(tz=datetime.UTC)
        stored = await operations.revoke_source_entitlement(
            execute,
            entitlement,
            revoked_at=original_revoked_at,
            revoked_by_transaction_id=_transaction_id(10),
        )
        timestamps = await load_source_entitlement_timestamps(entitlement)
        earlier = original_revoked_at - datetime.timedelta(days=1)

        returned = await operations.revoke_source_entitlement(
            execute,
            stored,
            revoked_at=earlier,
            revoked_by_transaction_id=_transaction_id(11),
        )

        assert returned == stored
        assert (
            await operations.load_source_entitlement(
                execute,
                entitlement.user_id,
                entitlement.kind_id,
                entitlement.grant_transaction_id,
            )
            == stored
        )
        assert await load_source_entitlement_timestamps(entitlement) == timestamps


class TestLoadSourceEntitlementsForSubscription:
    @pytest.mark.asyncio
    async def test_missing_subscription_returns_empty_list(self) -> None:
        loaded = await operations.load_source_entitlements_for_subscription(
            execute,
            new_subscription_id(),
        )

        assert loaded == []

    @pytest.mark.asyncio
    async def test_returns_all_linked_grants_in_kind_and_transaction_order(self) -> None:
        subscription_id = new_subscription_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        transaction_ids = _ordered_transaction_ids(6)
        active_month = make_source_entitlement(
            subscription_id=subscription_id,
            grant_transaction_id=transaction_ids[1],
            kind_id=EntitlementKindId.month_tokens,
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=1),
        )
        active_day = make_source_entitlement(
            subscription_id=subscription_id,
            grant_transaction_id=transaction_ids[0],
            user_id=active_month.user_id,
            kind_id=EntitlementKindId.day_tokens,
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=1),
        )
        expired = make_source_entitlement(
            subscription_id=subscription_id,
            grant_transaction_id=transaction_ids[2],
            user_id=active_month.user_id,
            starts_at=now - datetime.timedelta(days=2),
            expires_at=now,
        )
        future_day = make_source_entitlement(
            subscription_id=subscription_id,
            grant_transaction_id=transaction_ids[3],
            user_id=active_month.user_id,
            kind_id=EntitlementKindId.day_tokens,
            starts_at=now + datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=3),
        )
        never_active_future = make_source_entitlement(
            subscription_id=subscription_id,
            grant_transaction_id=transaction_ids[4],
            user_id=active_month.user_id,
            kind_id=EntitlementKindId.day_tokens,
            starts_at=now + datetime.timedelta(days=2),
            expires_at=now + datetime.timedelta(days=3),
            revoked_at=now + datetime.timedelta(days=1),
        )
        revoked = make_source_entitlement(
            subscription_id=subscription_id,
            grant_transaction_id=transaction_ids[5],
            user_id=active_month.user_id,
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=1),
            revoked_at=now,
        )
        unlinked = make_source_entitlement(
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=1),
        )
        for entitlement in (
            active_month,
            active_day,
            expired,
            future_day,
            never_active_future,
            revoked,
            unlinked,
        ):
            await operations.insert_source_entitlement(execute, entitlement)

        loaded = await operations.load_source_entitlements_for_subscription(
            execute,
            subscription_id,
        )

        assert loaded == [active_day, expired, future_day, never_active_future, revoked, active_month]


class TestLoadSourceEntitlementsForOneTimePurchase:
    @pytest.mark.asyncio
    async def test_missing_purchase_returns_empty_list(self) -> None:
        loaded = await operations.load_source_entitlements_for_one_time_purchase(
            execute,
            new_purchase_id(),
        )

        assert loaded == []

    @pytest.mark.asyncio
    async def test_returns_all_linked_grants_in_kind_and_transaction_order(self) -> None:
        one_time_purchase_id = new_purchase_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        transaction_ids = _ordered_transaction_ids(5)
        active_month = make_source_entitlement(
            one_time_purchase_id=one_time_purchase_id,
            grant_transaction_id=transaction_ids[1],
            kind_id=EntitlementKindId.month_tokens,
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=1),
        )
        active_day = make_source_entitlement(
            one_time_purchase_id=one_time_purchase_id,
            grant_transaction_id=transaction_ids[0],
            user_id=active_month.user_id,
            kind_id=EntitlementKindId.day_tokens,
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=1),
        )
        future_day = make_source_entitlement(
            one_time_purchase_id=one_time_purchase_id,
            grant_transaction_id=transaction_ids[3],
            user_id=active_month.user_id,
            kind_id=EntitlementKindId.day_tokens,
            starts_at=now + datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=3),
        )
        expired = make_source_entitlement(
            one_time_purchase_id=one_time_purchase_id,
            grant_transaction_id=transaction_ids[2],
            user_id=active_month.user_id,
            starts_at=now - datetime.timedelta(days=2),
            expires_at=now,
        )
        revoked = make_source_entitlement(
            one_time_purchase_id=one_time_purchase_id,
            grant_transaction_id=transaction_ids[4],
            user_id=active_month.user_id,
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=1),
            revoked_at=now,
        )
        other_purchase = make_source_entitlement(
            one_time_purchase_id=new_purchase_id(),
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=1),
        )
        for entitlement in (active_month, active_day, future_day, expired, revoked, other_purchase):
            await operations.insert_source_entitlement(execute, entitlement)

        loaded = await operations.load_source_entitlements_for_one_time_purchase(
            execute,
            one_time_purchase_id,
        )

        assert loaded == [active_day, expired, future_day, revoked, active_month]


class TestLoadSourceEntitlements:
    @pytest.mark.asyncio
    async def test_no_source_entitlements(self) -> None:
        assert (
            await operations.load_source_entitlements(
                execute,
                new_user_id(),
                EntitlementKindId.day_tokens,
            )
            == []
        )

    @pytest.mark.asyncio
    async def test_loads_all_grants_in_time_and_identity_order(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        later = make_source_entitlement(
            user_id=user_id,
            starts_at=now,
            expires_at=now + datetime.timedelta(days=2),
        )
        earlier = make_source_entitlement(
            user_id=user_id,
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=1),
        )
        await operations.insert_source_entitlement(execute, later)
        await operations.insert_source_entitlement(execute, earlier)

        loaded = await operations.load_source_entitlements(execute, user_id, EntitlementKindId.day_tokens)

        assert loaded == [earlier, later]


class TestLoadEffectiveIntervals:
    @pytest.mark.asyncio
    async def test_no_effective_intervals(self) -> None:
        assert (
            await operations.load_effective_intervals(
                execute,
                new_user_id(),
                EntitlementKindId.day_tokens,
                ending_after=datetime.datetime.min.replace(tzinfo=datetime.UTC),
            )
            == []
        )

    @pytest.mark.asyncio
    async def test_loads_intervals_ending_after_boundary(self) -> None:
        user_id = new_user_id()
        kind_id = EntitlementKindId.day_tokens
        now = datetime.datetime.now(tz=datetime.UTC)
        expired = make_effective_entitlement_interval(
            user_id=user_id,
            kind_id=kind_id,
            starts_at=now - datetime.timedelta(days=2),
            expires_at=now,
        )
        active = expired.replace(value=20, starts_at=now, expires_at=now + datetime.timedelta(days=1))

        async with transaction() as transaction_execute:
            await operations.replace_effective_intervals(transaction_execute, user_id, kind_id, [expired, active])

        assert await operations.load_effective_intervals(
            execute,
            user_id,
            kind_id,
            ending_after=now,
        ) == [active]


class TestReplaceEffectiveIntervals:
    @pytest.mark.asyncio
    async def test_replaces_complete_user_kind_timeline(self) -> None:
        user_id = new_user_id()
        kind_id = EntitlementKindId.day_tokens
        now = datetime.datetime.now(tz=datetime.UTC)
        first = make_effective_entitlement_interval(
            user_id=user_id,
            kind_id=kind_id,
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=1),
        )
        second = first.replace(value=20, starts_at=first.expires_at, expires_at=now + datetime.timedelta(days=2))

        async with transaction() as transaction_execute:
            await operations.replace_effective_intervals(transaction_execute, user_id, kind_id, [first, second])

        assert await operations.load_effective_intervals(
            execute,
            user_id,
            kind_id,
            ending_after=now,
        ) == [first, second]
        assert all(
            created_at == updated_at
            for created_at, updated_at in await load_effective_interval_timestamps(user_id, kind_id)
        )

        async with TableSizeDelta("en_entitlements", delta=-1):
            async with transaction() as transaction_execute:
                await operations.replace_effective_intervals(transaction_execute, user_id, kind_id, [second])

        assert await operations.load_effective_intervals(
            execute,
            user_id,
            kind_id,
            ending_after=now,
        ) == [second]

    @pytest.mark.asyncio
    async def test_empty_intervals_delete_complete_timeline(self) -> None:
        interval = make_effective_entitlement_interval()
        async with transaction() as transaction_execute:
            await operations.replace_effective_intervals(
                transaction_execute,
                interval.user_id,
                interval.kind_id,
                [interval],
            )

        async with TableSizeDelta("en_entitlements", delta=-1):
            async with transaction() as transaction_execute:
                await operations.replace_effective_intervals(
                    transaction_execute,
                    interval.user_id,
                    interval.kind_id,
                    [],
                )

        assert (
            await operations.load_effective_intervals(
                execute,
                interval.user_id,
                interval.kind_id,
                ending_after=datetime.datetime.min.replace(tzinfo=datetime.UTC),
            )
            == []
        )

    @pytest.mark.asyncio
    async def test_insert_failure_rolls_back_timeline_deletion(self) -> None:
        original = make_effective_entitlement_interval()
        async with transaction() as transaction_execute:
            await operations.replace_effective_intervals(
                transaction_execute,
                original.user_id,
                original.kind_id,
                [original],
            )
        duplicate = original.replace(value=20)
        unique_violation = cast(type[Exception], UniqueViolation)

        async with TableSizeNotChanged("en_entitlements"):
            with pytest.raises(unique_violation):
                async with transaction() as transaction_execute:
                    await operations.replace_effective_intervals(
                        transaction_execute,
                        original.user_id,
                        original.kind_id,
                        [duplicate, duplicate],
                    )

        assert await operations.load_effective_intervals(
            execute,
            original.user_id,
            original.kind_id,
            ending_after=datetime.datetime.min.replace(tzinfo=datetime.UTC),
        ) == [original]


class TestLoadActiveIntervals:
    @pytest.mark.asyncio
    async def test_half_open_interval(self) -> None:
        starts_at = datetime.datetime.now(tz=datetime.UTC)
        interval = make_effective_entitlement_interval(
            starts_at=starts_at,
            expires_at=starts_at + datetime.timedelta(days=1),
        )
        async with transaction() as transaction_execute:
            await operations.replace_effective_intervals(
                transaction_execute,
                interval.user_id,
                interval.kind_id,
                [interval],
            )

        assert await operations.load_active_intervals(
            execute,
            [interval.user_id],
            [interval.kind_id],
            evaluation_time=starts_at,
        ) == [interval]
        assert (
            await operations.load_active_intervals(
                execute,
                [interval.user_id],
                [interval.kind_id],
                evaluation_time=interval.expires_at,
            )
            == []
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("user_ids", "kind_ids"), [([], [EntitlementKindId.day_tokens]), ([new_user_id()], [])])
    async def test_empty_filter(self, user_ids: list[UserId], kind_ids: list[EntitlementKindId]) -> None:
        assert (
            await operations.load_active_intervals(
                execute,
                user_ids,
                kind_ids,
                evaluation_time=datetime.datetime.now(tz=datetime.UTC),
            )
            == []
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(("duplicate_users", "duplicate_kinds"), [(True, False), (False, True)])
    async def test_duplicate_filters(self, duplicate_users: bool, duplicate_kinds: bool) -> None:
        interval = make_effective_entitlement_interval()
        async with transaction() as transaction_execute:
            await operations.replace_effective_intervals(
                transaction_execute,
                interval.user_id,
                interval.kind_id,
                [interval],
            )
        user_ids = [interval.user_id, interval.user_id] if duplicate_users else [interval.user_id]
        kind_ids = [interval.kind_id, interval.kind_id] if duplicate_kinds else [interval.kind_id]

        assert await operations.load_active_intervals(
            execute,
            user_ids,
            kind_ids,
            evaluation_time=interval.starts_at,
        ) == [interval]


class TestDeleteExpiredEffectiveIntervals:
    @pytest.mark.asyncio
    async def test_no_expired_intervals(self) -> None:
        cleanup_time = datetime.datetime.min.replace(tzinfo=datetime.UTC)

        async with TableSizeNotChanged("en_entitlements"):
            deleted = await operations.delete_expired_effective_intervals(execute, cleanup_time)

        assert deleted == 0

    @pytest.mark.asyncio
    async def test_deletes_only_expired_intervals(self) -> None:
        user_id = new_user_id()
        now = datetime.datetime.now(tz=datetime.UTC)
        cleanup_time = now - datetime.timedelta(days=2)
        expired = make_effective_entitlement_interval(
            user_id=user_id,
            starts_at=now - datetime.timedelta(days=4),
            expires_at=cleanup_time,
        )
        active = expired.replace(starts_at=now, expires_at=now + datetime.timedelta(days=1))
        async with transaction() as transaction_execute:
            await operations.replace_effective_intervals(
                transaction_execute,
                user_id,
                EntitlementKindId.day_tokens,
                [expired, active],
            )

        async with TableSizeDelta("en_entitlements", delta=-1):
            deleted = await operations.delete_expired_effective_intervals(execute, cleanup_time)

        assert deleted == 1
        assert await operations.load_effective_intervals(
            execute,
            user_id,
            EntitlementKindId.day_tokens,
            ending_after=datetime.datetime.min.replace(tzinfo=datetime.UTC),
        ) == [active]
