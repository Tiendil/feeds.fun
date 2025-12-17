import pytest
from pytest_mock import MockerFixture

from ffun.auth import errors
from ffun.auth.domain import (
    import_user_to_external_service,
    logout_user_from_all_sessions,
    logout_user_from_all_sessions_in_service,
    remove_user_from_external_service,
)
from ffun.auth.settings import primary_oidc_service_id, single_user_service_id
from ffun.core import utils
from ffun.domain.entities import IdPId, UserId
from ffun.users import domain as u_domain


class TestRemoveUserFromExternalService:

    @pytest.mark.asyncio
    async def test_no_idp_found(self, external_user_id: str) -> None:
        with pytest.raises(errors.NoIdPFound):
            await remove_user_from_external_service(IdPId(666), external_user_id)

    @pytest.mark.asyncio
    async def test_remove_user(self, external_user_id: str, mocker: MockerFixture) -> None:
        remove_user = mocker.patch("ffun.auth.idps.no_idp.Plugin.remove_user")

        await remove_user_from_external_service(single_user_service_id, external_user_id)

        remove_user.assert_called_once_with(external_user_id)


class TestLogoutUserFromAllSessionsInService:

    @pytest.mark.asyncio
    async def test_no_idp_found(self, external_user_id: str) -> None:
        with pytest.raises(errors.NoIdPFound):
            await logout_user_from_all_sessions_in_service(IdPId(666), external_user_id)

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


class TestImportUserToExternalService:

    @pytest.mark.asyncio
    async def test_no_idp_found(self, external_user_id: str, external_user_email: str) -> None:
        with pytest.raises(errors.NoIdPFound):
            await import_user_to_external_service(
                service=IdPId(666),
                external_user_id=external_user_id,
                email=external_user_email,
                created_at=utils.now(),
                verify_internal_user_exists=False,
            )

    @pytest.mark.asyncio
    async def test_verify_internal_user_exists(self, external_user_id: str, external_user_email: str) -> None:
        with pytest.raises(errors.InternalUserDoesNotExistForImportedUser):
            await import_user_to_external_service(
                service=primary_oidc_service_id,
                external_user_id=external_user_id,
                email=external_user_email,
                created_at=utils.now(),
                verify_internal_user_exists=True,
            )

    @pytest.mark.asyncio
    async def test_success(self, external_user_id: str, external_user_email: str, mocker: MockerFixture) -> None:
        await u_domain.get_or_create_user_id(single_user_service_id, external_user_id)

        import_user = mocker.patch("ffun.auth.idps.no_idp.Plugin.import_user")

        now = utils.now()

        await import_user_to_external_service(
            service=single_user_service_id,
            external_user_id=external_user_id,
            email=external_user_email,
            created_at=now,
            verify_internal_user_exists=True,
        )

        import_user.assert_called_once_with(external_user_id, external_user_email, now)
