import pytest
from pytest_mock import MockerFixture

from ffun.auth.domain import remove_user_from_external_service
from ffun.users.entities import Service


class TestRemoveUserFromExternalService:

    @pytest.mark.asyncio
    async def test_remove_supertokens_user(self, external_user_id: str, mocker: MockerFixture):
        remove_supertokens_user = mocker.patch('ffun.auth.supertokens.remove_user')

        await remove_user_from_external_service(Service.supertokens, external_user_id)

        remove_supertokens_user.assert_called_once_with(external_user_id)

    @pytest.mark.asyncio
    async def test_remove_single_user(self, external_user_id: str, mocker: MockerFixture):
        remove_supertokens_user = mocker.patch('ffun.auth.supertokens.remove_user')

        await remove_user_from_external_service(Service.single, external_user_id)

        remove_supertokens_user.assert_not_called()
