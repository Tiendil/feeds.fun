import pytest
from pytest_mock import MockerFixture

from ffun.core.tests.helpers import assert_logs_has_business_event, assert_logs_has_no_business_event, capture_logs
from ffun.data_protection.domain import remove_user
from ffun.domain.domain import new_user_id
from ffun.domain.entities import UserId
from ffun.users.domain import get_user_external_ids


# TODO: add tests for multiple services when we'll support them
class TestRemoveUser:

    @pytest.mark.asyncio
    async def test_no_user(self) -> None:
        user_id = new_user_id()

        with capture_logs() as logs:
            await remove_user(user_id)

        assert_logs_has_no_business_event(logs, "user_removed")

    @pytest.mark.asyncio
    async def test_has_user_single_service(self, internal_user_id: UserId, mocker: MockerFixture) -> None:

        remove_user_from_external_service = mocker.patch("ffun.auth.domain.remove_user_from_external_service")

        assert await get_user_external_ids(internal_user_id)

        with capture_logs() as logs:
            await remove_user(internal_user_id)

        assert remove_user_from_external_service.call_count == 1

        assert not await get_user_external_ids(internal_user_id)

        assert_logs_has_business_event(logs, "user_removed", user_id=internal_user_id)
