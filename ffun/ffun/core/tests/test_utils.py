import datetime
from typing import cast
from unittest.mock import MagicMock

from ffun.core import utils


class TestHasTimezone:
    def test_timestamp_with_timezone(self) -> None:
        timestamp = datetime.datetime.now(tz=datetime.UTC)

        assert utils.has_timezone(timestamp)

    def test_timestamp_without_timezone(self) -> None:
        timestamp = datetime.datetime.now()

        assert not utils.has_timezone(timestamp)

    def test_timezone_without_offset(self) -> None:
        timestamp = MagicMock(spec=datetime.datetime)
        timestamp.tzinfo = MagicMock(spec=datetime.tzinfo)
        cast(MagicMock, timestamp.utcoffset).return_value = None

        assert not utils.has_timezone(timestamp)
