import pytest

from ffun.queues import domain, operations
from ffun.queues.entities import QueueKind
from ffun.queues.tests import make
from ffun.queues.tests.entities import FakeQueueItem


class TestPush:
    @pytest.mark.asyncio
    async def test_push(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        item = make.fake_queue_item()

        await domain.push(QueueKind.test_queue_1, [item])

        records = await operations.tech_get_queue_records(QueueKind.test_queue_1, FakeQueueItem)

        assert len(records) == 1
        assert records[0].item == item


class TestPull:
    @pytest.mark.asyncio
    async def test_pull(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        item = make.fake_queue_item()

        await operations.push(QueueKind.test_queue_1, [item])

        records = await domain.pull(QueueKind.test_queue_1, FakeQueueItem, limit=1)

        assert len(records) == 1
        assert records[0].item == item


class TestAcknowledge:
    @pytest.mark.asyncio
    async def test_acknowledge(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        item = make.fake_queue_item()

        await operations.push(QueueKind.test_queue_1, [item])
        records = await operations.tech_get_queue_records(QueueKind.test_queue_1, FakeQueueItem)

        record_id = records[0].id

        assert record_id is not None

        removed = await domain.acknowledge([record_id])

        assert removed == 1
