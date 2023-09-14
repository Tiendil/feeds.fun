import datetime
from typing import Type

import openai
import pytest
from pytest_mock import MockerFixture

from ffun.openai.entities import KeyStatus
from ffun.openai.keys_statuses import Statuses, StatusInfo, track_key_status


@pytest.fixture
def statuses():
    return Statuses()
