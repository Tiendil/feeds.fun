import pytest

from ffun.domain.datetime_intervals import month_interval_start
from ffun.domain.entities import UserId
from ffun.resources.domain import load_resource
from ffun.resources.operations import initialize_resource, try_to_reserve

_kind = 214
_another_kind = 215


class TestLoadResource:
    @pytest.mark.asyncio
    async def test_initialized(self, internal_user_id: UserId) -> None:
        interval_started_at = month_interval_start()

        await initialize_resource(user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at)

        await try_to_reserve(
            user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at, amount=13, limit=100
        )

        resource = await load_resource(user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at)

        assert resource.user_id == internal_user_id
        assert resource.kind == _kind
        assert resource.interval_started_at == interval_started_at
        assert resource.used == 0
        assert resource.reserved == 13

    @pytest.mark.asyncio
    async def test_not_initialized(self, internal_user_id: UserId) -> None:
        interval_started_at = month_interval_start()

        resource = await load_resource(user_id=internal_user_id, kind=_kind, interval_started_at=interval_started_at)

        assert resource.user_id == internal_user_id
        assert resource.kind == _kind
        assert resource.interval_started_at == interval_started_at
        assert resource.used == 0
        assert resource.reserved == 0
