import datetime
import enum
import uuid
from typing import Generic, NewType, TypeVar

from ffun.core.entities import BaseEntity

QueueRecordId = NewType("QueueRecordId", uuid.UUID)
QueueItemT = TypeVar("QueueItemT", bound="BaseQueueItem")

DEFAULT_SECONDARY_ID = 1


class QueueKind(enum.IntEnum):
    tag_processor = 1
    test_queue_1 = 1_000_000
    test_queue_2 = 1_000_001


class BaseQueueItem(BaseEntity):
    @classmethod
    def from_queue(cls: type[QueueItemT], raw: dict[str, object]) -> QueueItemT:
        return cls.model_validate(raw)

    def to_queue(self) -> dict[str, object]:
        return self.model_dump(mode="json")  # type: ignore[misc]


class QueueRecord(BaseEntity, Generic[QueueItemT]):
    id: QueueRecordId | None = None
    primary_id: QueueKind
    secondary_id: int = DEFAULT_SECONDARY_ID
    priority: int
    freezed_till: datetime.datetime
    created_at: datetime.datetime
    item: QueueItemT
