import datetime
import time

import pytest
from pytest_mock import MockerFixture

from ffun.core.tests.helpers import TableSizeDelta, TableSizeNotChanged
from ffun.queues import operations
from ffun.queues import settings as queues_settings
from ffun.queues.entities import QueueKind, QueueRecord
from ffun.queues.tests import helpers, make
from ffun.queues.tests.entities import FakeQueueItem

QueueKey = tuple[QueueKind, int]
QueueRecords = list[QueueRecord[FakeQueueItem]]


def record_value(record: QueueRecord[FakeQueueItem]) -> str:
    return record.item.value


class TestPush:
    @pytest.mark.asyncio
    async def test_empty_items(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        async with TableSizeNotChanged("q_items"):
            await operations.push(QueueKind.test_queue_1, [])

    @pytest.mark.asyncio
    async def test_default_priority(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        item = make.fake_queue_item()
        before_priority = time.time_ns()

        async with TableSizeDelta("q_items", delta=1):
            await operations.push(QueueKind.test_queue_1, [item])

        after_priority = time.time_ns()
        saved_items = await operations.tech_get_queue_records(QueueKind.test_queue_1, FakeQueueItem)

        assert len(saved_items) == 1

        saved_item = saved_items[0]
        assert saved_item.id is not None
        assert before_priority <= saved_item.priority <= after_priority
        assert saved_item.created_at is not None
        assert saved_item.freezed_till is not None
        assert saved_item.freezed_till <= datetime.datetime.now(tz=datetime.timezone.utc)
        assert saved_item.primary_id == QueueKind.test_queue_1
        assert saved_item.secondary_id == 1
        assert saved_item.item == item

    @pytest.mark.asyncio
    async def test_custom_priority(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        priority = 17

        saved_item = await helpers.push_item(priority=priority)

        assert saved_item.priority == priority

    @pytest.mark.asyncio
    async def test_multiple_items(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        items = [make.fake_queue_item(), make.fake_queue_item(), make.fake_queue_item()]

        async with TableSizeDelta("q_items", delta=3):
            await operations.push(QueueKind.test_queue_1, items)

        saved_items = await operations.tech_get_queue_records(QueueKind.test_queue_1, FakeQueueItem)

        assert len(saved_items) == 3
        assert {record_value(record) for record in saved_items} == {item.value for item in items}


class TestPull:
    @pytest.mark.asyncio
    async def test_no_items(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        items = await operations.pull(QueueKind.test_queue_1, FakeQueueItem, limit=3)

        assert items == []

    @pytest.mark.asyncio
    async def test_zero_limit(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        await helpers.push_item()

        items = await operations.pull(QueueKind.test_queue_1, FakeQueueItem, limit=0)

        assert items == []

    @pytest.mark.asyncio
    async def test_pull_first_item_by_priority(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        late_item = await helpers.push_item(priority=2)
        early_item = await helpers.push_item(priority=1)

        pulled_items = await operations.pull(QueueKind.test_queue_1, FakeQueueItem, limit=1)

        assert len(pulled_items) == 1
        pulled_item = pulled_items[0]
        assert pulled_item is not None
        assert pulled_item.id == early_item.id
        assert pulled_item.freezed_till is not None
        assert pulled_item.id != late_item.id

    @pytest.mark.asyncio
    async def test_pull_limited_number_of_items(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        items = [
            await helpers.push_item(priority=1),
            await helpers.push_item(priority=2),
            await helpers.push_item(priority=3),
        ]

        pulled_items = await operations.pull(QueueKind.test_queue_1, FakeQueueItem, limit=2)

        assert [item.id for item in pulled_items] == [items[0].id, items[1].id]

    @pytest.mark.asyncio
    async def test_pull_uses_configured_freezing_delay(self, mocker: MockerFixture) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        freezing_delay = datetime.timedelta(hours=2)
        mocker.patch.object(queues_settings.settings, "freezing_delay", freezing_delay)

        await helpers.push_item()

        pulled_items = await operations.pull(QueueKind.test_queue_1, FakeQueueItem, limit=1)

        assert len(pulled_items) == 1
        pulled_item = pulled_items[0]
        assert pulled_item.freezed_till > datetime.datetime.now(tz=datetime.timezone.utc) + datetime.timedelta(hours=1)

    @pytest.mark.asyncio
    async def test_pull_only_from_selected_secondary_queue(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        first_queue_item = await helpers.push_item(secondary_id=1)
        second_queue_item = await helpers.push_item(secondary_id=2)

        pulled_items = await operations.pull(QueueKind.test_queue_1, FakeQueueItem, limit=2, secondary_id=2)

        assert len(pulled_items) == 1
        pulled_item = pulled_items[0]
        assert pulled_item is not None
        assert pulled_item.id == second_queue_item.id
        assert pulled_item.id != first_queue_item.id

    @pytest.mark.asyncio
    async def test_pull_only_from_selected_queue_kind(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)
        await operations.tech_clear_queue(QueueKind.test_queue_2)

        first_kind_item = await helpers.push_item(queue_kind=QueueKind.test_queue_1)
        second_kind_item = await helpers.push_item(queue_kind=QueueKind.test_queue_2)

        pulled_items = await operations.pull(QueueKind.test_queue_2, FakeQueueItem, limit=2)

        assert len(pulled_items) == 1
        pulled_item = pulled_items[0]
        assert pulled_item is not None
        assert pulled_item.id == second_kind_item.id
        assert pulled_item.id != first_kind_item.id

    @pytest.mark.asyncio
    async def test_pull_and_acknowledge_are_scoped_by_queue_kind_and_secondary_id(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)
        await operations.tech_clear_queue(QueueKind.test_queue_2)

        records_by_queue: dict[QueueKey, QueueRecords] = {}

        for queue_kind in (QueueKind.test_queue_1, QueueKind.test_queue_2):
            for secondary_id in (1, 2):
                records_by_queue[(queue_kind, secondary_id)] = [
                    await helpers.push_item(queue_kind=queue_kind, secondary_id=secondary_id, priority=1),
                    await helpers.push_item(queue_kind=queue_kind, secondary_id=secondary_id, priority=2),
                ]

        for (queue_kind, secondary_id), records in records_by_queue.items():
            stored_records = await operations.tech_get_queue_records(
                queue_kind, FakeQueueItem, secondary_id=secondary_id
            )

            assert [record.id for record in stored_records] == [record.id for record in records]

        target_records = records_by_queue[(QueueKind.test_queue_1, 2)]
        pulled_target_records = await operations.pull(QueueKind.test_queue_1, FakeQueueItem, limit=10, secondary_id=2)

        assert [record.id for record in pulled_target_records] == [record.id for record in target_records]
        assert await operations.pull(QueueKind.test_queue_1, FakeQueueItem, limit=10, secondary_id=2) == []

        pulled_same_kind_other_secondary = await operations.pull(
            QueueKind.test_queue_1, FakeQueueItem, limit=10, secondary_id=1
        )
        pulled_other_kind_same_secondary = await operations.pull(
            QueueKind.test_queue_2, FakeQueueItem, limit=10, secondary_id=2
        )

        assert [record.id for record in pulled_same_kind_other_secondary] == [
            record.id for record in records_by_queue[(QueueKind.test_queue_1, 1)]
        ]
        assert [record.id for record in pulled_other_kind_same_secondary] == [
            record.id for record in records_by_queue[(QueueKind.test_queue_2, 2)]
        ]

        acknowledged = await operations.acknowledge([record.id for record in pulled_target_records if record.id])

        assert acknowledged == len(target_records)
        assert await operations.tech_get_queue_records(QueueKind.test_queue_1, FakeQueueItem, secondary_id=2) == []

        untouched_records = await operations.tech_get_queue_records(
            QueueKind.test_queue_2, FakeQueueItem, secondary_id=1
        )

        assert [record.id for record in untouched_records] == [
            record.id for record in records_by_queue[(QueueKind.test_queue_2, 1)]
        ]

    @pytest.mark.asyncio
    async def test_pulled_item_is_hidden_until_acknowledged(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        saved_item = await helpers.push_item()

        first_pull = await operations.pull(QueueKind.test_queue_1, FakeQueueItem, limit=1)
        second_pull = await operations.pull(QueueKind.test_queue_1, FakeQueueItem, limit=1)

        assert len(first_pull) == 1
        assert first_pull[0].id == saved_item.id
        assert second_pull == []

    @pytest.mark.asyncio
    async def test_pulled_item_is_available_after_freeze_expires(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        saved_item = await helpers.push_item()

        first_pull = await operations.pull(QueueKind.test_queue_1, FakeQueueItem, limit=1)

        assert len(first_pull) == 1
        assert first_pull[0].id == saved_item.id
        assert saved_item.id is not None

        await helpers.set_freezed_till(
            saved_item.id,
            datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(seconds=1),
        )

        second_pull = await operations.pull(QueueKind.test_queue_1, FakeQueueItem, limit=1)

        assert len(second_pull) == 1
        assert second_pull[0].id == saved_item.id


class TestAcknowledge:
    @pytest.mark.asyncio
    async def test_no_items(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        async with TableSizeNotChanged("q_items"):
            acknowledged = await operations.acknowledge([])

        assert acknowledged == 0

    @pytest.mark.asyncio
    async def test_existing_item(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        saved_item = await helpers.push_item()

        assert saved_item.id is not None

        async with TableSizeDelta("q_items", delta=-1):
            acknowledged = await operations.acknowledge([saved_item.id])

        assert acknowledged == 1
        assert await operations.tech_get_queue_records(QueueKind.test_queue_1, FakeQueueItem) == []

    @pytest.mark.asyncio
    async def test_multiple_existing_items(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        await operations.push(
            QueueKind.test_queue_1,
            [make.fake_queue_item(), make.fake_queue_item(), make.fake_queue_item()],
        )

        saved_items = await operations.tech_get_queue_records(QueueKind.test_queue_1, FakeQueueItem)

        first_record_id = saved_items[0].id
        second_record_id = saved_items[1].id
        third_record_id = saved_items[2].id

        assert first_record_id is not None
        assert second_record_id is not None
        assert third_record_id is not None

        async with TableSizeDelta("q_items", delta=-2):
            acknowledged = await operations.acknowledge([first_record_id, second_record_id])

        assert acknowledged == 2

        left_items = await operations.tech_get_queue_records(QueueKind.test_queue_1, FakeQueueItem)

        assert [item.id for item in left_items] == [third_record_id]

    @pytest.mark.asyncio
    async def test_missing_item(self) -> None:
        await operations.tech_clear_queue(QueueKind.test_queue_1)

        saved_item = await helpers.push_item()

        assert saved_item.id is not None

        await operations.acknowledge([saved_item.id])

        async with TableSizeNotChanged("q_items"):
            acknowledged = await operations.acknowledge([saved_item.id])

        assert acknowledged == 0
