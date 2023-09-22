import datetime
import uuid

import pytest

from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.resources import errors
from ffun.resources.domain import load_resource, month_interval_start
from ffun.resources.operations import (
    convert_reserved_to_used,
    initialize_resource,
    load_resource_history,
    load_resources,
    try_to_reserve,
)


@pytest.fixture
def interval_started_at() -> datetime.datetime:
    return month_interval_start()


_kind = 214
_another_kind = 215


class TestInitializeResource:
    @pytest.mark.asyncio
    async def test_new_record(self, internal_user_id: uuid.UUID, interval_started_at: datetime.datetime) -> None:
        async with TableSizeDelta("r_resources", delta=1):
            resource = await initialize_resource(
                user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at
            )

        assert resource.user_id == internal_user_id
        assert resource.kind == _kind
        assert resource.interval_started_at == interval_started_at
        assert resource.used == 0
        assert resource.reserved == 0

        async with TableSizeNotChanged("r_resources"):
            loaded_resource = await load_resource(
                user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at
            )

        assert loaded_resource == resource

    @pytest.mark.asyncio
    async def test_do_not_reinitialized_if_exists(
        self, internal_user_id: uuid.UUID, interval_started_at: datetime.datetime
    ) -> None:
        await initialize_resource(user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at)

        await try_to_reserve(
            user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at, amount=1, limit=100
        )

        async with TableSizeNotChanged("r_resources"):
            resource = await initialize_resource(
                user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at
            )

        assert resource.reserved == 1

        loaded_resource = await load_resource(
            user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at
        )

        assert loaded_resource == resource


class TestLoadResources:
    """Most functionality are tested in other classes."""

    @pytest.mark.asyncio
    async def test_initialize_if_not_found(
        self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID, interval_started_at: datetime.datetime
    ) -> None:
        await initialize_resource(user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at)

        await try_to_reserve(
            user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at, amount=13, limit=100
        )

        async with TableSizeDelta("r_resources", delta=1):
            resources = await load_resources(
                user_ids=[internal_user_id, another_internal_user_id],
                kind=_kind,
                interval_started_at=interval_started_at,
            )

        assert len(resources) == 2

        resource_1 = resources[internal_user_id]

        assert resource_1.user_id == internal_user_id
        assert resource_1.kind == _kind
        assert resource_1.interval_started_at == interval_started_at
        assert resource_1.used == 0
        assert resource_1.reserved == 13

        resource_2 = resources[another_internal_user_id]

        assert resource_2.user_id == another_internal_user_id
        assert resource_2.kind == _kind
        assert resource_2.interval_started_at == interval_started_at
        assert resource_2.used == 0
        assert resource_2.reserved == 0


class TestTryToReserve:
    @pytest.mark.parametrize("amount", [0, 1, 100])
    @pytest.mark.asyncio
    async def test_for_not_existed_resource(
        self, amount: int, internal_user_id: uuid.UUID, interval_started_at: datetime.datetime
    ) -> None:
        result = await try_to_reserve(
            user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at, amount=amount, limit=100
        )

        assert result

        resource = await load_resource(user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at)

        assert resource.used == 0
        assert resource.reserved == amount

    @pytest.mark.asyncio
    async def test_for_existed_resource(
        self, internal_user_id: uuid.UUID, interval_started_at: datetime.datetime
    ) -> None:
        result = await try_to_reserve(
            user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at, amount=1, limit=100
        )

        result = await try_to_reserve(
            user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at, amount=13, limit=100
        )

        assert result

        resource = await load_resource(user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at)

        assert resource.used == 0
        assert resource.reserved == 14

    @pytest.mark.asyncio
    async def test_not_enough(self, internal_user_id: uuid.UUID, interval_started_at: datetime.datetime) -> None:
        result = await try_to_reserve(
            user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at, amount=101, limit=100
        )

        assert not result


class TestConvertReservedToUsed:
    @pytest.mark.parametrize(
        "reserved, converted_reserved, converted_used, expected_reserved, expected_used",
        [(13, 13, 9, 0, 9), (13, 13, 13, 0, 13), (77, 14, 13, 63, 13)],
    )
    @pytest.mark.asyncio
    async def test_converted(  # noqa: CFQ002
        self,
        internal_user_id: uuid.UUID,
        interval_started_at: datetime.datetime,
        reserved: int,
        converted_reserved: int,
        converted_used: int,
        expected_reserved: int,
        expected_used: int,
    ) -> None:
        await try_to_reserve(
            user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at, amount=reserved, limit=100
        )

        await convert_reserved_to_used(
            user_id=internal_user_id,
            kind=_kind,
            interval_started_at=interval_started_at,
            reserved=converted_reserved,
            used=converted_used,
        )

        resource = await load_resource(user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at)

        assert resource.used == expected_used
        assert resource.reserved == expected_reserved

    @pytest.mark.asyncio
    async def test_not_enough(self, internal_user_id: uuid.UUID, interval_started_at: datetime.datetime) -> None:
        await try_to_reserve(
            user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at, amount=13, limit=100
        )

        with pytest.raises(errors.CanNotConvertReservedToUsed):
            await convert_reserved_to_used(
                user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at, reserved=14, used=13
            )

    @pytest.mark.asyncio
    async def test_no_resource(self, internal_user_id: uuid.UUID, interval_started_at: datetime.datetime) -> None:
        with pytest.raises(errors.CanNotConvertReservedToUsed):
            await convert_reserved_to_used(
                user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at, reserved=0, used=13
            )


class TestLoadResourceHistory:
    @pytest.mark.asyncio
    async def test_no_history(self, internal_user_id: uuid.UUID) -> None:
        history = await load_resource_history(user_id=internal_user_id, kind=_kind)

        assert len(history) == 0

    @pytest.mark.asyncio
    async def test_with_history(self, internal_user_id: uuid.UUID, another_internal_user_id: uuid.UUID) -> None:
        internal_1 = datetime.datetime(2020, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        internal_2 = datetime.datetime(2020, 2, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        internal_3 = datetime.datetime(2020, 3, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)

        await try_to_reserve(
            user_id=internal_user_id, kind=_kind, interval_started_at=internal_1, amount=13, limit=100
        )

        await try_to_reserve(
            user_id=internal_user_id, kind=_kind, interval_started_at=internal_3, amount=14, limit=100
        )

        await try_to_reserve(
            user_id=another_internal_user_id, kind=_kind, interval_started_at=internal_2, amount=15, limit=100
        )

        await try_to_reserve(
            user_id=internal_user_id, kind=_another_kind, interval_started_at=internal_3, amount=16, limit=100
        )

        history = await load_resource_history(user_id=internal_user_id, kind=_kind)

        assert len(history) == 2

        assert history[0].user_id == internal_user_id
        assert history[0].interval_started_at == internal_3
        assert history[0].reserved == 14

        assert history[1].user_id == internal_user_id
        assert history[1].interval_started_at == internal_1
        assert history[1].reserved == 13

        history = await load_resource_history(user_id=another_internal_user_id, kind=_kind)

        assert len(history) == 1

        assert history[0].user_id == another_internal_user_id
        assert history[0].interval_started_at == internal_2
        assert history[0].reserved == 15
