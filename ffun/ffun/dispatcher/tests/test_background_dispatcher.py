import pytest
from pytest_mock import MockerFixture

from ffun.dispatcher import settings as dispatcher_settings
from ffun.dispatcher.background_dispatcher import EntriesDispatcher
from ffun.dispatcher.tests import make


class TestEntriesDispatcher:
    @pytest.mark.asyncio
    async def test_single_run__uses_configured_limits(self, mocker: MockerFixture) -> None:
        dispatch_entries = mocker.patch("ffun.dispatcher.background_dispatcher.domain.dispatch_entries")

        processors = (make.processor_dispatch_info(101), make.processor_dispatch_info(102))
        dispatcher = EntriesDispatcher(
            processors=processors,
            batch_size=5,
            concurrency=3,
            name="test_dispatcher",
            delay_between_runs=1,
        )

        await dispatcher.single_run()

        dispatch_entries.assert_awaited_once_with(processors=processors, batch_size=5, concurrency=3)

    @pytest.mark.asyncio
    async def test_single_run__uses_default_limits_from_settings(self, mocker: MockerFixture) -> None:
        mocker.patch.object(dispatcher_settings.settings, "dispatch_batch_size", 17)
        mocker.patch.object(dispatcher_settings.settings, "dispatch_concurrency", 7)
        dispatch_entries = mocker.patch("ffun.dispatcher.background_dispatcher.domain.dispatch_entries")

        processors = (make.processor_dispatch_info(101), make.processor_dispatch_info(102))
        dispatcher = EntriesDispatcher(processors=processors, name="test_dispatcher", delay_between_runs=1)

        await dispatcher.single_run()

        dispatch_entries.assert_awaited_once_with(processors=processors, batch_size=17, concurrency=7)
