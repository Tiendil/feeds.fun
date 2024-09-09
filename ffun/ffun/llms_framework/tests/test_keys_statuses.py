import datetime

from pytest_mock import MockerFixture

from ffun.llms_framework.entities import KeyStatus
from ffun.llms_framework.keys_statuses import Statuses


class TestStatuses:
    def test_inititalization(self, api_key_statuses: Statuses) -> None:
        assert api_key_statuses._statuses == {}

    def test_set_status(self, api_key_statuses: Statuses) -> None:
        status_1, status_2, *_ = list(KeyStatus)

        api_key_statuses.set("key_1", status_1)
        api_key_statuses.set("key_2", status_2)

        assert api_key_statuses.get("key_1") == status_1
        assert api_key_statuses.get("key_2") == status_2

    def test_get__no_key(self, api_key_statuses: Statuses) -> None:
        assert api_key_statuses.get("key_1") == KeyStatus.unknown

    def test_get__works(self, api_key_statuses: Statuses) -> None:
        api_key_statuses.set("key_1", KeyStatus.works)
        assert api_key_statuses.get("key_1") == KeyStatus.works

    def test_get__broken(self, api_key_statuses: Statuses) -> None:
        api_key_statuses.set("key_1", KeyStatus.broken)
        assert api_key_statuses.get("key_1") == KeyStatus.broken

    def test_get__broken_expired(self, api_key_statuses: Statuses, mocker: MockerFixture) -> None:
        api_key_statuses.set("key_1", KeyStatus.broken)

        mocker.patch("ffun.llms_framework.settings.settings.key_broken_timeout", datetime.timedelta(seconds=0))

        assert api_key_statuses.get("key_1") == KeyStatus.unknown

    def test_get__quota(self, api_key_statuses: Statuses) -> None:
        api_key_statuses.set("key_1", KeyStatus.quota)
        assert api_key_statuses.get("key_1") == KeyStatus.quota

    def test_get__quota_expired(self, api_key_statuses: Statuses, mocker: MockerFixture) -> None:
        api_key_statuses.set("key_1", KeyStatus.quota)

        mocker.patch("ffun.llms_framework.settings.settings.key_quota_timeout", datetime.timedelta(seconds=0))

        assert api_key_statuses.get("key_1") == KeyStatus.unknown
