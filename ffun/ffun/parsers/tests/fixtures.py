import pytest

from ffun.parsers.tests.helpers import feeds_fixtures_directory, feeds_fixtures_names


@pytest.fixture
def raw_feed_content() -> str:
    fixture_filename = feeds_fixtures_names()[0]

    with open(feeds_fixtures_directory / fixture_filename, encoding="utf-8") as f:
        return f.read()


@pytest.fixture
def another_raw_feed_content() -> str:
    fixture_filename = feeds_fixtures_names()[1]

    with open(feeds_fixtures_directory / fixture_filename, encoding="utf-8") as f:
        return f.read()
