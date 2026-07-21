import asyncio
import datetime
from typing import cast

import pytest
from psycopg.errors import UniqueViolation
from pydantic import ValidationError

from ffun.core.postgresql import execute, transaction
from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.domain.domain import new_user_id
from ffun.entitlements import errors, operations
from ffun.entitlements.entities import EntitlementKindId, EntitlementSourceId
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
        now = datetime.datetime.now(tz=datetime.UTC)
        interval = make_effective_entitlement_interval(
            user_id=new_user_id(),
            kind_id=EntitlementKindId.day_tokens,
            value=10,
            starts_at=now,
            expires_at=now + datetime.timedelta(days=1),
        )

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
        )

        assert loaded is None

    @pytest.mark.asyncio
    async def test_loads_source_entitlement(self) -> None:
        entitlement = make_source_entitlement()

        async with TableSizeDelta("en_source_entitlements", delta=1):
            await operations.upsert_source_entitlement(execute, entitlement)

        assert (
            await operations.load_source_entitlement(
                execute,
                entitlement.user_id,
                entitlement.kind_id,
                entitlement.source,
            )
            == entitlement
        )


class TestUpsertSourceEntitlement:
    @pytest.mark.asyncio
    async def test_inserts_grant(self) -> None:
        entitlement = make_source_entitlement()

        async with TableSizeDelta("en_source_entitlements", delta=1):
            await operations.upsert_source_entitlement(execute, entitlement)

        assert (
            await operations.load_source_entitlement(
                execute,
                entitlement.user_id,
                entitlement.kind_id,
                entitlement.source,
            )
            == entitlement
        )

        created_at, updated_at = await load_source_entitlement_timestamps(entitlement)
        assert created_at == updated_at

    @pytest.mark.asyncio
    async def test_inserts_revocation(self) -> None:
        entitlement = make_source_entitlement(granted=False, value=None)

        async with TableSizeDelta("en_source_entitlements", delta=1):
            await operations.upsert_source_entitlement(execute, entitlement)

        assert (
            await operations.load_source_entitlement(
                execute,
                entitlement.user_id,
                entitlement.kind_id,
                entitlement.source,
            )
            == entitlement
        )

        created_at, updated_at = await load_source_entitlement_timestamps(entitlement)
        assert created_at == updated_at

    @pytest.mark.asyncio
    async def test_replaces_grant(self) -> None:
        entitlement = make_source_entitlement()

        async with TableSizeDelta("en_source_entitlements", delta=1):
            await operations.upsert_source_entitlement(execute, entitlement)

        created_at, _ = await load_source_entitlement_timestamps(entitlement)

        await asyncio.sleep(0.001)

        replacement = entitlement.to_granted(
            value=20,
            starts_at=entitlement.starts_at,
            expires_at=entitlement.expires_at,
        )

        async with TableSizeNotChanged("en_source_entitlements"):
            await operations.upsert_source_entitlement(execute, replacement)

        loaded = await operations.load_source_entitlement(
            execute,
            entitlement.user_id,
            entitlement.kind_id,
            entitlement.source,
        )
        assert loaded == replacement

        replaced_created_at, replaced_updated_at = await load_source_entitlement_timestamps(replacement)
        assert replaced_created_at == created_at
        assert replaced_updated_at > created_at

    @pytest.mark.asyncio
    async def test_replaces_with_revocation(self) -> None:
        entitlement = make_source_entitlement()

        async with TableSizeDelta("en_source_entitlements", delta=1):
            await operations.upsert_source_entitlement(execute, entitlement)

        replacement = entitlement.to_revoked(
            starts_at=entitlement.starts_at,
            expires_at=entitlement.expires_at,
        )

        async with TableSizeNotChanged("en_source_entitlements"):
            await operations.upsert_source_entitlement(execute, replacement)

        assert (
            await operations.load_source_entitlement(
                execute,
                entitlement.user_id,
                entitlement.kind_id,
                entitlement.source,
            )
            == replacement
        )

    @pytest.mark.asyncio
    async def test_replaces_revocation_with_grant(self) -> None:
        entitlement = make_source_entitlement(granted=False, value=None)

        async with TableSizeDelta("en_source_entitlements", delta=1):
            await operations.upsert_source_entitlement(execute, entitlement)

        replacement = entitlement.to_granted(
            value=20,
            starts_at=entitlement.starts_at,
            expires_at=entitlement.expires_at,
        )

        async with TableSizeNotChanged("en_source_entitlements"):
            await operations.upsert_source_entitlement(execute, replacement)

        assert (
            await operations.load_source_entitlement(
                execute,
                entitlement.user_id,
                entitlement.kind_id,
                entitlement.source,
            )
            == replacement
        )


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
    async def test_loads_all_sources_in_time_order(self) -> None:
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
        await operations.upsert_source_entitlement(execute, later)
        await operations.upsert_source_entitlement(execute, earlier)

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
            value=10,
            starts_at=now - datetime.timedelta(days=2),
            expires_at=now,
        )
        active = expired.replace(
            value=20,
            starts_at=now,
            expires_at=now + datetime.timedelta(days=1),
        )

        async with TableSizeDelta("en_entitlements", delta=2):
            async with transaction() as transaction_execute:
                await operations.replace_effective_intervals(
                    transaction_execute,
                    user_id,
                    kind_id,
                    [expired, active],
                )

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
            value=10,
            starts_at=now - datetime.timedelta(days=1),
            expires_at=now + datetime.timedelta(days=1),
        )
        second = first.replace(value=20, starts_at=first.expires_at, expires_at=now + datetime.timedelta(days=2))

        async with TableSizeDelta("en_entitlements", delta=2):
            async with transaction() as transaction_execute:
                await operations.replace_effective_intervals(transaction_execute, user_id, kind_id, [first, second])

        loaded = await operations.load_effective_intervals(
            execute,
            user_id,
            kind_id,
            ending_after=now,
        )
        assert loaded == [first, second]

        timestamp_rows = await load_effective_interval_timestamps(user_id, kind_id)
        assert len(timestamp_rows) == 2
        assert all(created_at == updated_at for created_at, updated_at in timestamp_rows)

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
        user_id = new_user_id()
        kind_id = EntitlementKindId.day_tokens
        now = datetime.datetime.now(tz=datetime.UTC)
        interval = make_effective_entitlement_interval(
            user_id=user_id,
            kind_id=kind_id,
            value=10,
            starts_at=now,
            expires_at=now + datetime.timedelta(days=1),
        )

        async with TableSizeDelta("en_entitlements", delta=1):
            async with transaction() as transaction_execute:
                await operations.replace_effective_intervals(transaction_execute, user_id, kind_id, [interval])

        async with TableSizeDelta("en_entitlements", delta=-1):
            async with transaction() as transaction_execute:
                await operations.replace_effective_intervals(transaction_execute, user_id, kind_id, [])

        assert (
            await operations.load_effective_intervals(
                execute,
                user_id,
                kind_id,
                ending_after=now,
            )
            == []
        )

    @pytest.mark.asyncio
    async def test_insert_failure_rolls_back_timeline_deletion(self) -> None:
        user_id = new_user_id()
        kind_id = EntitlementKindId.day_tokens
        now = datetime.datetime.now(tz=datetime.UTC)
        original = make_effective_entitlement_interval(
            user_id=user_id,
            kind_id=kind_id,
            value=10,
            starts_at=now,
            expires_at=now + datetime.timedelta(days=1),
        )

        async with transaction() as transaction_execute:
            await operations.replace_effective_intervals(transaction_execute, user_id, kind_id, [original])

        duplicate = original.replace(value=20)
        unique_violation = cast(type[Exception], UniqueViolation)

        async with TableSizeNotChanged("en_entitlements"):
            with pytest.raises(unique_violation):
                async with transaction() as transaction_execute:
                    await operations.replace_effective_intervals(
                        transaction_execute,
                        user_id,
                        kind_id,
                        [duplicate, duplicate],
                    )

        assert await operations.load_effective_intervals(
            execute,
            user_id,
            kind_id,
            ending_after=now,
        ) == [original]


class TestLoadActiveIntervals:
    @pytest.mark.asyncio
    async def test_half_open_interval(self) -> None:
        user_id = new_user_id()
        kind_id = EntitlementKindId.day_tokens
        starts_at = datetime.datetime.now(tz=datetime.UTC)
        interval = make_effective_entitlement_interval(
            user_id=user_id,
            kind_id=kind_id,
            value=10,
            starts_at=starts_at,
            expires_at=starts_at + datetime.timedelta(days=1),
        )

        async with transaction() as transaction_execute:
            await operations.replace_effective_intervals(transaction_execute, user_id, kind_id, [interval])

        assert await operations.load_active_intervals(execute, [user_id], [kind_id], evaluation_time=starts_at) == [
            interval
        ]
        assert (
            await operations.load_active_intervals(execute, [user_id], [kind_id], evaluation_time=interval.expires_at)
            == []
        )

    @pytest.mark.asyncio
    async def test_empty_user_filter(self) -> None:
        assert (
            await operations.load_active_intervals(
                execute,
                [],
                [EntitlementKindId.day_tokens],
                evaluation_time=datetime.datetime.now(tz=datetime.UTC),
            )
            == []
        )

    @pytest.mark.asyncio
    async def test_empty_kind_filter(self) -> None:
        assert (
            await operations.load_active_intervals(
                execute,
                [new_user_id()],
                [],
                evaluation_time=datetime.datetime.now(tz=datetime.UTC),
            )
            == []
        )

    @pytest.mark.asyncio
    async def test_duplicate_user_filter(self) -> None:
        interval = make_effective_entitlement_interval()

        async with TableSizeDelta("en_entitlements", delta=1):
            async with transaction() as transaction_execute:
                await operations.replace_effective_intervals(
                    transaction_execute,
                    interval.user_id,
                    interval.kind_id,
                    [interval],
                )

        assert await operations.load_active_intervals(
            execute,
            [interval.user_id, interval.user_id],
            [interval.kind_id],
            evaluation_time=interval.starts_at,
        ) == [interval]

    @pytest.mark.asyncio
    async def test_duplicate_kind_filter(self) -> None:
        interval = make_effective_entitlement_interval()

        async with TableSizeDelta("en_entitlements", delta=1):
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
            [interval.kind_id, interval.kind_id],
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
        kind_id = EntitlementKindId.day_tokens
        now = datetime.datetime.now(tz=datetime.UTC)
        cleanup_time = now - datetime.timedelta(days=2)
        expired = make_effective_entitlement_interval(
            user_id=user_id,
            kind_id=kind_id,
            value=10,
            starts_at=now - datetime.timedelta(days=4),
            expires_at=cleanup_time,
        )
        active = expired.replace(
            starts_at=now,
            expires_at=now + datetime.timedelta(days=1),
        )

        async with transaction() as transaction_execute:
            await operations.replace_effective_intervals(transaction_execute, user_id, kind_id, [expired, active])

        async with TableSizeDelta("en_entitlements", delta=-1):
            deleted = await operations.delete_expired_effective_intervals(execute, cleanup_time)

        assert deleted == 1
        assert await operations.load_effective_intervals(
            execute,
            user_id,
            kind_id,
            ending_after=datetime.datetime.min.replace(tzinfo=datetime.UTC),
        ) == [active]
