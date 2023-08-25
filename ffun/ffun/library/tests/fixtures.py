import uuid

import pytest

from ffun.library.entities import Entry
from ffun.library.tests import make as l_make


# TODO: replace with fixture of real entry from the DB
@pytest.fixture
def fake_entry(loaded_feed_id: uuid.UUID) -> Entry:
    return l_make.fake_entry(loaded_feed_id)
