import pytest
from pytest_mock import MockerFixture

from ffun.dispatcher import settings as dispatcher_settings
from ffun.dispatcher.background_dispatcher import EntriesDispatcher
from ffun.dispatcher.tests import make


class TestEntriesDispatcher:
    @pytest.mark.asyncio
    async def test_single_run__uses_configured_chunk(self, mocker: MockerFixture) -> None:
        dispatch_entries = mocker.patch("ffun.dispatcher.background_dispatcher.domain.dispatch_entries")

        processors = (make.processor_dispatch_info(101), make.processor_dispatch_info(102))
        dispatcher = EntriesDispatcher(processors=processors, chunk=5, name="test_dispatcher", delay_between_runs=1)

        await dispatcher.single_run()

        dispatch_entries.assert_awaited_once_with(processors=processors, limit=5)

    @pytest.mark.asyncio
    async def test_single_run__uses_default_chunk_from_settings(self, mocker: MockerFixture) -> None:
        mocker.patch.object(dispatcher_settings.settings, "dispatch_chunk", 17)
        dispatch_entries = mocker.patch("ffun.dispatcher.background_dispatcher.domain.dispatch_entries")

        processors = (make.processor_dispatch_info(101), make.processor_dispatch_info(102))
        dispatcher = EntriesDispatcher(processors=processors, name="test_dispatcher", delay_between_runs=1)

        await dispatcher.single_run()

        dispatch_entries.assert_awaited_once_with(processors=processors, limit=17)
