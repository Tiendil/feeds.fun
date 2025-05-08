import uuid

import pytest

from ffun.core.postgresql import execute
from ffun.core.tests.helpers import (
    Delta,
    TableSizeDelta,
    TableSizeNotChanged,
    assert_logs_has_business_event,
    assert_logs_has_no_business_event,
    capture_logs,
)
from ffun.core.utils import now
from ffun.domain.domain import new_user_id
from ffun.domain.entities import UserId
from ffun.users import errors
from ffun.users.entities import Service
from ffun.users.operations import (
    add_mapping,
    count_total_users,
    get_mapping,
    get_user_external_ids,
    store_user,
    unlink_user,
)


class TestAddMapping:

    @pytest.mark.asyncio
    async def test_new_user(self, external_user_id: str) -> None:
        with capture_logs() as logs:
            async with TableSizeDelta("u_users", delta=1):
                async with TableSizeDelta("u_mapping", delta=1):
                    internal_user_id = await add_mapping(Service.supertokens, external_user_id)

        assert await get_mapping(Service.supertokens, external_user_id) == internal_user_id

        assert_logs_has_business_event(logs, "user_created", user_id=internal_user_id)

    @pytest.mark.asyncio
    async def test_different_service(self, external_user_id: str) -> None:
        async with TableSizeDelta("u_users", delta=2):
            async with TableSizeDelta("u_mapping", delta=2):
                internal_user_id_1 = await add_mapping(Service.supertokens, external_user_id)
                internal_user_id_2 = await add_mapping(Service.single, external_user_id)

        assert await get_mapping(Service.supertokens, external_user_id) == internal_user_id_1
        assert await get_mapping(Service.single, external_user_id) == internal_user_id_2

    @pytest.mark.asyncio
    async def test_existing_user(self, external_user_id: str, internal_user_id: UserId) -> None:
        with capture_logs() as logs:
            async with TableSizeNotChanged("u_users"):
                async with TableSizeNotChanged("u_mapping"):
                    assert await add_mapping(Service.supertokens, external_user_id) == internal_user_id

        assert await get_mapping(Service.supertokens, external_user_id) == internal_user_id

        assert_logs_has_no_business_event(logs, "user_created")


# most of functionality are tested in other tests
class TestGetMapping:

    @pytest.mark.asyncio
    async def test_no_user_found(self, external_user_id: str) -> None:
        with pytest.raises(errors.NoUserMappingFound):
            await get_mapping(Service.supertokens, external_user_id)

    @pytest.mark.asyncio
    async def test_no_user_found_for_another_service(self, external_user_id: str) -> None:
        await add_mapping(Service.supertokens, external_user_id)

        with pytest.raises(errors.NoUserMappingFound):
            await get_mapping(Service.single, external_user_id)


class TestCountTotalUsers:

    @pytest.mark.asyncio
    async def test(self) -> None:
        async with Delta(count_total_users, delta=3):
            for _ in range(3):
                await add_mapping(Service.supertokens, uuid.uuid4().hex)


class TestStoreUser:

    @pytest.mark.asyncio
    async def test_new_user(self) -> None:
        user_id = new_user_id()

        async with TableSizeDelta("u_users", delta=1):
            await store_user(execute, user_id)

        result = await execute("SELECT * FROM u_users WHERE id = %(id)s", {"id": user_id})

        assert len(result) == 1
        assert result[0]["id"] == user_id

    @pytest.mark.asyncio
    async def test_existing_user(self) -> None:
        user_id = new_user_id()

        await store_user(execute, user_id)

        timestamp = now()

        async with TableSizeNotChanged("u_users"):
            await store_user(execute, user_id)

        result = await execute("SELECT * FROM u_users WHERE id = %(id)s", {"id": user_id})

        assert len(result) == 1
        assert result[0]["id"] == user_id
        assert result[0]["created_at"] < timestamp


# currently we do not support multiple mappings for the same user
# TODO: add tests for multiple mappings when we support it
class TestGetUserExternalIds:

    @pytest.mark.asyncio
    async def test_no_mappings(self) -> None:
        user_id = new_user_id()
        assert await get_user_external_ids(user_id) == {}

    @pytest.mark.asyncio
    async def test_single_mappings(self, internal_user_id: UserId, external_user_id: str) -> None:
        mapping = await get_user_external_ids(internal_user_id)

        assert mapping == {Service.supertokens: external_user_id}


# TODO: add tests for multiple mappings when we support it
class TestUnlinkUser:

    @pytest.mark.asyncio
    async def test_no_mappings(self) -> None:
        user_id = new_user_id()
        async with TableSizeNotChanged("u_mapping"):
            await unlink_user(Service.supertokens, user_id)

    @pytest.mark.asyncio
    async def test_single_mappings(self, internal_user_id: UserId) -> None:
        async with TableSizeNotChanged("u_users"):
            async with TableSizeDelta("u_mapping", delta=-1):
                await unlink_user(Service.supertokens, internal_user_id)

        mapping = await get_user_external_ids(internal_user_id)

        assert mapping == {}
