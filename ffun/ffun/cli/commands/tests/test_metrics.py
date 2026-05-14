import pytest
from pytest_mock import MockerFixture

from ffun.cli.commands import metrics
from ffun.cli.commands.metrics import _snapshot_at
from ffun.queues import operations as q_operations
from ffun.queues.entities import QueueKind
from ffun.queues.tests import helpers as q_helpers


class TestSystemSliceQueues:
    @pytest.mark.asyncio
    async def test_measure_queue_sizes(self, mocker: MockerFixture) -> None:
        first_processor_id = 101
        second_processor_id = 202

        for queue_kind in QueueKind:
            await q_operations.tech_clear_queue(queue_kind)

        await q_helpers.push_item(queue_kind=QueueKind.entries_to_process)
        await q_helpers.push_item(queue_kind=QueueKind.entries_to_process)
        await q_helpers.push_item(queue_kind=QueueKind.entries_to_process)
        await q_helpers.push_item(queue_kind=QueueKind.entries_to_tag, secondary_id=first_processor_id)
        await q_helpers.push_item(queue_kind=QueueKind.entries_to_tag, secondary_id=first_processor_id)
        await q_helpers.push_item(queue_kind=QueueKind.entries_to_tag, secondary_id=second_processor_id)
        await q_helpers.push_item(queue_kind=QueueKind.test_queue_1)

        business_slice = mocker.patch.object(metrics.logger, "business_slice")

        await metrics.system_slice_queues()

        business_slice.assert_any_call(
            "queue_size", user_id=None, primary_id=1, secondary_id=1, total=3, snapshot_at=_snapshot_at
        )
        business_slice.assert_any_call(
            "queue_size",
            user_id=None,
            primary_id=2,
            secondary_id=first_processor_id,
            total=2,
            snapshot_at=_snapshot_at,
        )
        business_slice.assert_any_call(
            "queue_size",
            user_id=None,
            primary_id=2,
            secondary_id=second_processor_id,
            total=1,
            snapshot_at=_snapshot_at,
        )
        business_slice.assert_any_call(
            "queue_size",
            user_id=None,
            primary_id=1_000_000,
            secondary_id=1,
            total=1,
            snapshot_at=_snapshot_at,
        )

        assert business_slice.call_count == 4
