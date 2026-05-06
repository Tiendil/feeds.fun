import uuid

from ffun.queues.tests.entities import FakeQueueItem


def fake_queue_item() -> FakeQueueItem:
    return FakeQueueItem(value=str(uuid.uuid4()))
