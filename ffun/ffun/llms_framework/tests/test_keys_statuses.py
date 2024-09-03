import datetime

from pytest_mock import MockerFixture

from ffun.llms_framework.entities import KeyStatus
from ffun.llms_framework.keys_statuses import Statuses


class TestStatuses:
    def test_inititalization(self, statuses: Statuses) -> None:
        assert statuses._statuses == {}

    def test_set_status(self, statuses: Statuses) -> None:
        status_1, status_2, *_ = list(KeyStatus)

        statuses.set("key_1", status_1)
        statuses.set("key_2", status_2)

        assert statuses.get("key_1") == status_1
        assert statuses.get("key_2") == status_2

    def test_get__no_key(self, statuses: Statuses) -> None:
        assert statuses.get("key_1") == KeyStatus.unknown

    def test_get__works(self, statuses: Statuses) -> None:
        statuses.set("key_1", KeyStatus.works)
        assert statuses.get("key_1") == KeyStatus.works

    def test_get__broken(self, statuses: Statuses) -> None:
        statuses.set("key_1", KeyStatus.broken)
        assert statuses.get("key_1") == KeyStatus.broken

    def test_get__broken_expired(self, statuses: Statuses, mocker: MockerFixture) -> None:
        statuses.set("key_1", KeyStatus.broken)

        mocker.patch("ffun.openai.settings.settings.key_broken_timeout", datetime.timedelta(seconds=0))

        assert statuses.get("key_1") == KeyStatus.unknown

    def test_get__quota(self, statuses: Statuses) -> None:
        statuses.set("key_1", KeyStatus.quota)
        assert statuses.get("key_1") == KeyStatus.quota

    def test_get__quota_expired(self, statuses: Statuses, mocker: MockerFixture) -> None:
        statuses.set("key_1", KeyStatus.quota)

        mocker.patch("ffun.openai.settings.settings.key_quota_timeout", datetime.timedelta(seconds=0))

        assert statuses.get("key_1") == KeyStatus.unknown