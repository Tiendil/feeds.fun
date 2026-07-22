import asyncio
import datetime
from typing import cast

import pytest
from psycopg.errors import UniqueViolation
from pydantic import ValidationError

from ffun.core.postgresql import execute, transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.domain.domain import new_user_id
from ffun.domain.entities import UserId
from ffun.entitlements import errors, operations
from ffun.entitlements.entities import EntitlementKindId, EntitlementSourceId, EntitlementTransactionId
from ffun.entitlements.tests.helpers import load_effective_interval_timestamps, load_source_entitlement_timestamps
from ffun.entitlements.tests.make import make_effective_entitlement_interval, make_source_entitlement


class TestRowToSourceEntitlement:
    def test_converts_row(self) -> None:
        entitlement = make_source_entitlement()

        assert operations.row_to_source_entitlement(entitlement.model_dump()) == entitlement  # type: ignore[misc]

    def test_invalid_row_raises_module_error(self) -> None:
        with pytest.raises(errors.InvalidStoredEntitlement) as exception_info:
            operations.row_to_source_entitlement({})

        assert "entity_kind=source_entitlement" in str(exception_info.value)
        assert isinstance(exception_info.value.__cause__, ValidationError)


class TestRowToEffectiveInterval:
    def test_converts_row(self) -> None:
        interval = make_effective_entitlement_interval()

        assert operations.row_to_effective_interval(interval.model_dump()) == interval  # type: ignore[misc]

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
            EntitlementSourceId("missing"),
            EntitlementTransactionId("missing"),
        )

        assert loaded is None

    @pytest.mark.asyncio
    async def test_identity_includes_transaction(self) -> None:
        entitlement = make_source_entitlement()

        async with TableSizeDelta("en_source_entitlements", delta=1):
            await operations.insert_source_entitlement(execute, entitlement)

        assert (
            await operations.load_source_entitlement(
                execute,
                entitlement.user_id,
                entitlement.kind_id,
                entitlement.source,
                entitlement.transaction_id,
            )
            == entitlement
        )
        assert (
            await operations.load_source_entitlement(
                execute,
                entitlement.user_id,
                entitlement.kind_id,
                entitlement.source,
                EntitlementTransactionId("other"),
            )
            is None
        )


class TestInsertSourceEntitlement:
    @pytest.mark.asyncio
    async def test_inserts_immutable_grant(self) -> None:
        entitlement = make_source_entitlement()

        async with TableSizeDelta("en_source_entitlements", delta=1):
            await operations.insert_source_entitlement(execute, entitlement)

        created_at, updated_at = await load_source_entitlement_timestamps(entitlement)
        assert created_at == updated_at

    @pytest.mark.asyncio
    async def test_same_source_can_insert_multiple_transactions(self) -> None:
        first = make_source_entitlement()
        second = first.replace(transaction_id=EntitlementTransactionId("second"), value=20)

        async with TableSizeDelta("en_source_entitlements", delta=2):
            await operations.insert_source_entitlement(execute, first)
            await operations.insert_source_entitlement(execute, second)

        assert await operations.load_source_entitlements(execute, first.user_id, first.kind_id) == [second, first]

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
                entitlement.source,
                entitlement.transaction_id,
            )
            == entitlement
        )


class TestRevokeSourceEntitlement:
    @pytest.mark.asyncio
    async def test_sets_only_revocation_and_updated_timestamp(self) -> None:
        entitlement = make_source_entitlement()
        await operations.insert_source_entitlement(execute, entitlement)
        created_at, _ = await load_source_entitlement_timestamps(entitlement)
        await asyncio.sleep(0.001)
        revoked_at = datetime.datetime.now(tz=datetime.UTC)

        async with TableSizeNotChanged("en_source_entitlements"):
            await operations.revoke_source_entitlement(execute, entitlement, revoked_at=revoked_at)

        loaded = await operations.load_source_entitlement(
            execute,
            entitlement.user_id,
            entitlement.kind_id,
            entitlement.source,
            entitlement.transaction_id,
        )
        assert loaded == entitlement.to_revoked(revoked_at=revoked_at)
        revoked_created_at, revoked_updated_at = await load_source_entitlement_timestamps(entitlement)
        assert revoked_created_at == created_at
        assert revoked_updated_at > created_at

    @pytest.mark.asyncio
    async def test_already_revoked_row_is_not_changed(self) -> None:
        entitlement = make_source_entitlement()
        await operations.insert_source_entitlement(execute, entitlement)
        original_revoked_at = datetime.datetime.now(tz=datetime.UTC)
        await operations.revoke_source_entitlement(execute, entitlement, revoked_at=original_revoked_at)
        timestamps = await load_source_entitlement_timestamps(entitlement)

        await operations.revoke_source_entitlement(
            execute,
            entitlement,
            revoked_at=original_revoked_at + datetime.timedelta(days=1),
        )

        loaded = await operations.load_source_entitlement(
            execute,
            entitlement.user_id,
            entitlement.kind_id,
            entitlement.source,
            entitlement.transaction_id,
        )
        assert loaded is not None
        assert loaded.revoked_at == original_revoked_at
        assert await load_source_entitlement_timestamps(entitlement) == timestamps


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
            source=EntitlementSourceId("later"),
            starts_at=now,
            expires_at=now + datetime.timedelta(days=2),
        )
        earlier = make_source_entitlement(
            user_id=user_id,
            source=EntitlementSourceId("earlier"),
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
