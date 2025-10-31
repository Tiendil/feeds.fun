
from unittest import mock
import pytest

from starlette.datastructures import Headers

from ffun.auth.dependencies import _single_user, _oidc_user, _oidc_optional_user
from ffun.auth.settings import primary_oidc_service_id, single_user_service_id, settings, primary_oidc_service, single_user_service
from ffun.auth import errors
from ffun.users import domain as u_domain


class TestSingleUser:

    @pytest.mark.asyncio
    async def test_single_user(self) -> None:
        user = await _single_user()

        external_ids = await u_domain.get_user_external_ids(user.id)

        assert external_ids == {single_user_service_id: settings.single_user.external_id}

        loaded_user = await u_domain.get_or_create_user(
            single_user_service_id,
            settings.single_user.external_id
        )

        assert user == loaded_user


class _TestOIDCUser:
    user_accessor = NotImplemented

    @pytest.mark.asyncio
    async def test_no_identity_provider_id_header(self, external_user_id: str) -> None:
        request = mock.MagicMock()

        request.headers = Headers({settings.oidc.header_user_id: external_user_id})

        with pytest.raises(errors.OIDCNoIdentityProviderIdHeader):
            await self.user_accessor(request)

    @pytest.mark.asyncio
    async def test_no_identity_provider_in_settings(self, external_user_id: str) -> None:
        request = mock.MagicMock()

        request.headers = Headers({
            settings.oidc.header_user_id: external_user_id,
            settings.oidc.header_identity_provider_id: "unknown-provider"
        })

        with pytest.raises(errors.OIDCNoIdentityProviderInSettings):
            await self.user_accessor(request)

    @pytest.mark.asyncio
    async def test_user_processed(self, external_user_id: str) -> None:
        request = mock.MagicMock()

        request.headers = Headers({
            settings.oidc.header_user_id: external_user_id,
            settings.oidc.header_identity_provider_id: primary_oidc_service
        })

        user = await self.user_accessor(request)

        external_ids = await u_domain.get_user_external_ids(user.id)

        assert external_ids == {primary_oidc_service_id: external_user_id}

        loaded_user = await u_domain.get_or_create_user(
            primary_oidc_service_id,
            external_user_id
        )

        assert user == loaded_user


class TestOIDCUser(_TestOIDCUser):
    user_accessor = staticmethod(_oidc_user)

    @pytest.mark.asyncio
    async def test_no_user_id_header(self) -> None:
        request = mock.MagicMock()

        request.headers = Headers({})

        with pytest.raises(errors.OIDCNoUserIdHerader):
            await self.user_accessor(request)


class TestOIDCOptionalUser(_TestOIDCUser):
    user_accessor = staticmethod(_oidc_optional_user)

    @pytest.mark.asyncio
    async def test_no_user_id_header(self) -> None:
        request = mock.MagicMock()

        request.headers = Headers({})

        user = await self.user_accessor(request)

        assert user is None
