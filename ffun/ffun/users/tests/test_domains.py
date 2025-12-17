import pytest

from ffun.auth.settings import primary_oidc_service_id
from ffun.domain.entities import UserId
from ffun.users import operations
from ffun.users.domain import check_external_user_exists, get_or_create_user, get_or_create_user_id


class TestCheckExternalUserExists:

    @pytest.mark.asyncio
    async def test_user_exists(self, external_user_id: str, internal_user_id: UserId) -> None:
        assert internal_user_id
        assert await check_external_user_exists(primary_oidc_service_id, external_user_id)

    @pytest.mark.asyncio
    async def test_user_does_not_exist(self, external_user_id: str) -> None:
        assert not await check_external_user_exists(primary_oidc_service_id, external_user_id)


class TestGetOrCreateUserId:

    @pytest.mark.asyncio
    async def test_create_new_user(self, external_user_id: str) -> None:
        assert not await check_external_user_exists(primary_oidc_service_id, external_user_id)

        internal_user_id = await get_or_create_user_id(primary_oidc_service_id, external_user_id)

        external_ids = await operations.get_user_external_ids(internal_user_id)

        assert external_ids[primary_oidc_service_id] == external_user_id

    @pytest.mark.asyncio
    async def test_get_existing_user(self, external_user_id: str, internal_user_id: UserId) -> None:
        fetched_user_id = await get_or_create_user_id(primary_oidc_service_id, external_user_id)

        assert fetched_user_id == internal_user_id


class TestGetOrCreateUser:

    @pytest.mark.asyncio
    async def test_create_new_user(self, external_user_id: str) -> None:
        assert not await check_external_user_exists(primary_oidc_service_id, external_user_id)

        internal_user = await get_or_create_user(
            primary_oidc_service_id,
            external_user_id,
        )

        external_ids = await operations.get_user_external_ids(internal_user.id)

        assert external_ids[primary_oidc_service_id] == external_user_id

    @pytest.mark.asyncio
    async def test_get_existing_user(self, external_user_id: str, internal_user_id: UserId) -> None:
        internal_user = await get_or_create_user(
            primary_oidc_service_id,
            external_user_id,
        )

        assert internal_user.id == internal_user_id
