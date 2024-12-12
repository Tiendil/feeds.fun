
import os
from pathlib import Path
import pytest

from ffun.parsers.tests.helpers import feeds_fixtures_names, feeds_fixtures_directory


@pytest.fixture
def raw_feed_content() -> str:
    fixture_filename = feeds_fixtures_names()[0]

    with open(feeds_fixtures_directory / fixture_filename, encoding="utf-8") as f:
        return f.read()
