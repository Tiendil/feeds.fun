import pytest
import typer

from ffun.cli.commands import queues
from ffun.queues import operations as q_operations
from ffun.queues.entities import QueueKind
from ffun.queues.tests import helpers as q_helpers
from ffun.queues.tests.entities import FakeQueueItem


class TestQueueKindFromString:
    def test_by_name(self) -> None:
        assert queues.queue_kind_from_string("entries_to_process") == QueueKind.entries_to_process

    def test_by_int(self) -> None:
        assert queues.queue_kind_from_string(str(QueueKind.entries_to_tag.value)) == QueueKind.entries_to_tag

    def test_unknown_queue(self) -> None:
        with pytest.raises(typer.BadParameter):
            queues.queue_kind_from_string("unknown")


class TestValidateCleanupRequest:
    def test_all_request(self) -> None:
        queues.validate_cleanup_request(clean_all=True, queue=None, subqueue=None)

    def test_queue_request(self) -> None:
        queues.validate_cleanup_request(clean_all=False, queue="entries_to_process", subqueue=None)

    def test_subqueue_request(self) -> None:
        queues.validate_cleanup_request(clean_all=False, queue="entries_to_process", subqueue=17)

    def test_all_can_not_be_combined_with_queue(self) -> None:
        with pytest.raises(typer.BadParameter):
            queues.validate_cleanup_request(clean_all=True, queue="entries_to_process", subqueue=None)

    def test_all_can_not_be_combined_with_subqueue(self) -> None:
        with pytest.raises(typer.BadParameter):
            queues.validate_cleanup_request(clean_all=True, queue=None, subqueue=17)

    def test_subqueue_requires_queue(self) -> None:
        with pytest.raises(typer.BadParameter):
            queues.validate_cleanup_request(clean_all=False, queue=None, subqueue=17)

    def test_requires_all_or_queue(self) -> None:
        with pytest.raises(typer.BadParameter):
            queues.validate_cleanup_request(clean_all=False, queue=None, subqueue=None)


class TestCleanupQueues:
    @pytest.mark.asyncio
    async def test_all_queues(self) -> None:
        for queue_kind in QueueKind:
            await q_operations.tech_clear_queue(queue_kind)

        await q_helpers.push_item(queue_kind=QueueKind.test_queue_1)
        await q_helpers.push_item(queue_kind=QueueKind.test_queue_1, secondary_id=2)
        await q_helpers.push_item(queue_kind=QueueKind.test_queue_2)

        await queues.cleanup_queues(clean_all=True, queue=None, subqueue=None)

        assert await q_operations.queues_stats() == {}

    @pytest.mark.asyncio
    async def test_primary_queue(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.test_queue_1)
        await q_operations.tech_clear_queue(QueueKind.test_queue_2)

        await q_helpers.push_item(queue_kind=QueueKind.test_queue_1)
        left_record = await q_helpers.push_item(queue_kind=QueueKind.test_queue_2)

        await queues.cleanup_queues(clean_all=False, queue=QueueKind.test_queue_1.name, subqueue=None)

        assert await q_operations.tech_get_queue_records(QueueKind.test_queue_1, FakeQueueItem) == []
        assert await q_operations.tech_get_queue_records(QueueKind.test_queue_2, FakeQueueItem) == [left_record]

    @pytest.mark.asyncio
    async def test_subqueue(self) -> None:
        await q_operations.tech_clear_queue(QueueKind.test_queue_1)

        left_record = await q_helpers.push_item(queue_kind=QueueKind.test_queue_1, secondary_id=1)
        await q_helpers.push_item(queue_kind=QueueKind.test_queue_1, secondary_id=2)

        await queues.cleanup_queues(clean_all=False, queue=str(QueueKind.test_queue_1.value), subqueue=2)

        assert await q_operations.tech_get_queue_records(QueueKind.test_queue_1, FakeQueueItem) == [left_record]
        assert await q_operations.tech_get_queue_records(QueueKind.test_queue_1, FakeQueueItem, secondary_id=2) == []

    @pytest.mark.asyncio
    async def test_requires_all_or_queue(self) -> None:
        with pytest.raises(typer.BadParameter):
            await queues.cleanup_queues(clean_all=False, queue=None, subqueue=None)

    @pytest.mark.asyncio
    async def test_all_can_not_be_combined_with_queue(self) -> None:
        with pytest.raises(typer.BadParameter):
            await queues.cleanup_queues(clean_all=True, queue=QueueKind.test_queue_1.name, subqueue=None)
