import pytest
from pytest_mock import MockerFixture

from ffun.auth.domain import (
    logout_user_from_all_sessions,
    logout_user_from_all_sessions_in_service,
    remove_user_from_external_service,
)
from ffun.auth.settings import primary_oidc_service_id, single_user_service_id
from ffun.domain.entities import UserId


class TestRemoveUserFromExternalService:

    @pytest.mark.asyncio
    async def test_remove_user(self, external_user_id: str, mocker: MockerFixture) -> None:
        remove_user = mocker.patch("ffun.auth.idps.no_idp.Plugin.remove_user")

        await remove_user_from_external_service(single_user_service_id, external_user_id)

        remove_user.assert_called_once_with(external_user_id)


class TestLogoutUserFromAllSessionsInService:

    @pytest.mark.asyncio
    async def test_logout_user(self, external_user_id: str, mocker: MockerFixture) -> None:
        logout_user = mocker.patch("ffun.auth.idps.no_idp.Plugin.revoke_all_user_sessions")

        await logout_user_from_all_sessions_in_service(single_user_service_id, external_user_id)

        logout_user.assert_called_once_with(external_user_id)


class TestLogoutUserFromAllSessions:

    @pytest.mark.asyncio
    async def test_logout_user(self, internal_user_id: UserId, mocker: MockerFixture) -> None:
        get_user_external_ids = mocker.patch("ffun.users.domain.get_user_external_ids")
        get_user_external_ids.return_value = {primary_oidc_service_id: "oidc_id", single_user_service_id: "single_id"}

        logout_user = mocker.patch("ffun.auth.domain.logout_user_from_all_sessions_in_service")

        await logout_user_from_all_sessions(internal_user_id)

        assert logout_user.call_count == 2

        logout_user.assert_any_call(primary_oidc_service_id, "oidc_id")
        logout_user.assert_any_call(single_user_service_id, "single_id")
