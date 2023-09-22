import contextlib
import datetime
from typing import Generator

import openai

from ffun.core import utils
from ffun.openai.entities import KeyStatus
from ffun.openai.settings import settings


class StatusInfo:
    __slots__ = ("status", "updated_at")

    def __init__(self, status: KeyStatus, updated_at: datetime.datetime) -> None:
        self.status = status
        self.updated_at = updated_at


class Statuses:
    __slots__ = ("_statuses",)

    def __init__(self) -> None:
        self._statuses: dict[str, StatusInfo] = {}

    def set(self, key: str, status: KeyStatus) -> None:
        self._statuses[key] = StatusInfo(status, utils.now())

    def get(self, key: str) -> KeyStatus:
        info = self._statuses.get(key)

        if info is None:
            return KeyStatus.unknown

        if info.status == KeyStatus.works:
            return KeyStatus.works

        if info.status == KeyStatus.broken and info.updated_at + settings.key_broken_timeout > utils.now():
            return KeyStatus.broken

        if info.status == KeyStatus.quota and info.updated_at + settings.key_quota_timeout > utils.now():
            return KeyStatus.quota

        return KeyStatus.unknown


statuses = Statuses()


@contextlib.contextmanager
def track_key_status(key: str, statuses: Statuses = statuses) -> Generator[None, None, None]:
    try:
        yield
        statuses.set(key, KeyStatus.works)
    except openai.error.AuthenticationError:
        statuses.set(key, KeyStatus.broken)
        raise
    except openai.error.RateLimitError:
        statuses.set(key, KeyStatus.quota)
        raise
    except openai.error.PermissionError:
        statuses.set(key, KeyStatus.broken)
        raise
    except openai.error.InvalidAPIType:
        statuses.set(key, KeyStatus.broken)
        raise
    # TODO: test
    except openai.error.APIError:
        statuses.set(key, KeyStatus.unknown)
        raise
