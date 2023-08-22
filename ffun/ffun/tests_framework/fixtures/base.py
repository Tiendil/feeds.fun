import uuid

import pytest

from .. import utils as tf_utils


@pytest.fixture(name="fake_url")
def fixture_fake_url() -> str:
    return tf_utils.fake_url()
