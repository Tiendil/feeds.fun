from unittest import mock

import pytest
from starlette.datastructures import Headers

from ffun.auth import errors
from ffun.auth.dependencies import _idp_user
from ffun.auth.settings import primary_oidc_service, primary_oidc_service_id, settings
from ffun.users import domain as u_domain


class _TestIdPUser:
    user_accessor = NotImplemented

    @pytest.mark.asyncio
    async def test_no_identity_provider_id_header(self, external_user_id: str) -> None:
        request = mock.MagicMock()

        request.headers = Headers({settings.header_user_id: external_user_id})

        with pytest.raises(errors.IdPNoIdentityProviderIdHeader):
            await self.user_accessor(request)  # type: ignore

    @pytest.mark.asyncio
    async def test_empty_identity_provider_id_header(self, external_user_id: str) -> None:
        request = mock.MagicMock()

        request.headers = Headers(
            {settings.header_user_id: external_user_id, settings.header_identity_provider_id: ""}
        )

        with pytest.raises(errors.IdPNoIdentityProviderIdHeader):
            await self.user_accessor(request)  # type: ignore

    @pytest.mark.asyncio
    async def test_no_identity_provider_in_settings(self, external_user_id: str) -> None:
        request = mock.MagicMock()

        request.headers = Headers(
            {settings.header_user_id: external_user_id, settings.header_identity_provider_id: "unknown-provider"}
        )

        with pytest.raises(errors.IdPNoIdentityProviderInSettings):
            await self.user_accessor(request)  # type: ignore

    @pytest.mark.asyncio
    async def test_user_processed(self, external_user_id: str) -> None:
        request = mock.MagicMock()

        request.headers = Headers(
            {settings.header_user_id: external_user_id, settings.header_identity_provider_id: primary_oidc_service}
        )

        user = await self.user_accessor(request)  # type: ignore

        external_ids = await u_domain.get_user_external_ids(user.id)

        assert external_ids == {primary_oidc_service_id: external_user_id}

        loaded_user = await u_domain.get_or_create_user(primary_oidc_service_id, external_user_id)

        assert user == loaded_user


class TestIdPUser(_TestIdPUser):
    user_accessor = staticmethod(_idp_user)  # type: ignore

    @pytest.mark.asyncio
    async def test_no_user_id_header(self) -> None:
        request = mock.MagicMock()

        request.headers = Headers({})

        with pytest.raises(errors.IdPNoUserIdHeader):
            await self.user_accessor(request)

    @pytest.mark.asyncio
    async def test_empty_user_id_header(self) -> None:
        request = mock.MagicMock()

        request.headers = Headers({settings.header_user_id: ""})

        with pytest.raises(errors.IdPNoUserIdHeader):
            await self.user_accessor(request)
