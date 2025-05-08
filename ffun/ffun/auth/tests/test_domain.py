import pytest
from pytest_mock import MockerFixture

from ffun.auth.domain import (
    logout_user_from_all_sessions,
    logout_user_from_all_sessions_in_service,
    remove_user_from_external_service,
)
from ffun.domain.entities import UserId
from ffun.users.entities import Service


class TestRemoveUserFromExternalService:

    @pytest.mark.asyncio
    async def test_remove_supertokens_user(self, external_user_id: str, mocker: MockerFixture) -> None:
        remove_supertokens_user = mocker.patch("ffun.auth.supertokens.remove_user")

        await remove_user_from_external_service(Service.supertokens, external_user_id)

        remove_supertokens_user.assert_called_once_with(external_user_id)

    @pytest.mark.asyncio
    async def test_remove_single_user(self, external_user_id: str, mocker: MockerFixture) -> None:
        remove_supertokens_user = mocker.patch("ffun.auth.supertokens.remove_user")

        await remove_user_from_external_service(Service.single, external_user_id)

        remove_supertokens_user.assert_not_called()


class TestLogoutUserFromAllSessionsInService:

    @pytest.mark.asyncio
    async def test_logout_supertokens_user(self, external_user_id: str, mocker: MockerFixture) -> None:
        logout_supertokens_user = mocker.patch("ffun.auth.supertokens.logout_user_from_all_sessions")

        await logout_user_from_all_sessions_in_service(Service.supertokens, external_user_id)

        logout_supertokens_user.assert_called_once_with(external_user_id)

    @pytest.mark.asyncio
    async def test_logout_single_user(self, external_user_id: str, mocker: MockerFixture) -> None:
        logout_supertokens_user = mocker.patch("ffun.auth.supertokens.logout_user_from_all_sessions")

        await logout_user_from_all_sessions_in_service(Service.single, external_user_id)

        logout_supertokens_user.assert_not_called()


class TestLogoutUserFromAllSessions:

    @pytest.mark.asyncio
    async def test_logout_user(self, internal_user_id: UserId, mocker: MockerFixture) -> None:
        get_user_external_ids = mocker.patch("ffun.users.domain.get_user_external_ids")
        get_user_external_ids.return_value = {Service.supertokens: "supertokens_id", Service.single: "single_id"}

        logout_user = mocker.patch("ffun.auth.domain.logout_user_from_all_sessions_in_service")

        await logout_user_from_all_sessions(internal_user_id)

        assert logout_user.call_count == 2

        logout_user.assert_any_call(Service.supertokens, "supertokens_id")
        logout_user.assert_any_call(Service.single, "single_id")
