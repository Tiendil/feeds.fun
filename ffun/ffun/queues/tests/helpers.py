import datetime

from ffun.core.postgresql import execute
from ffun.queues import operations
from ffun.queues.entities import QueueKind, QueueRecord, QueueRecordId
from ffun.queues.tests import make
from ffun.queues.tests.entities import FakeQueueItem


async def push_item(
    item: FakeQueueItem | None = None,
    queue_kind: QueueKind = QueueKind.test_queue_1,
    secondary_id: int = 1,
    priority: int | None = None,
) -> QueueRecord[FakeQueueItem]:
    item = item or make.fake_queue_item()

    await operations.push(
        queue_kind,
        [item],
        secondary_id=secondary_id,
        priority=priority,
    )

    records = await operations.tech_get_queue_records(
        queue_kind,
        FakeQueueItem,
        secondary_id=secondary_id,
    )

    found_records = [record for record in records if record.item.value == item.value]

    assert len(found_records) == 1

    return found_records[0]


async def set_freezed_till(record_id: QueueRecordId, freezed_till: datetime.datetime) -> None:
    sql = """
    UPDATE q_items
    SET freezed_till = %(freezed_till)s
    WHERE id = %(record_id)s
    """

    await execute(sql, {"record_id": record_id, "freezed_till": freezed_till})  # type: ignore
