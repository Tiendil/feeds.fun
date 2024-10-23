
import asyncio
import pytest
from unittest import mock
from pytest_mock import MockerFixture
from structlog.testing import capture_logs
from structlog import contextvars as structlog_contextvars
from ffun.core.logging import MeasuringBoundLoggerMixin, get_module_logger
from ffun.core.tests.helpers import assert_logs, assert_logs_levels, assert_log_context_vars


logger = get_module_logger()


class TestMeasuringBoundLoggerMixin:
    """Test mixin methods after they applied to the logger class.

    Because it is more convinient, rather than testing the mixin itself.

    ATTENTION: `capture_logs` does not apply processorts => does not merge `m_labels`
               => we test them separately where it is possible
    """

    def test_measure__no_labels(self):
        with capture_logs() as logs:
            logger.measure("my_event", 42)
            assert_log_context_vars()

        assert logs == [{'module': 'ffun.core.tests.test_logging', 'm_kind': 'measure', 'm_value': 42, 'event': 'my_event', 'log_level': 'info'}]

    def test_measure__has_labels(self, mocker: MockerFixture):
        bound_measure_labels = mocker.patch('ffun.core.logging.bound_measure_labels')

        with capture_logs() as logs:
            logger.measure("my_event", 42, x="a", y=2)

        assert logs == [{'module': 'ffun.core.tests.test_logging', 'm_kind': 'measure', 'm_value': 42, 'event': 'my_event', 'log_level': 'info'}]

        bound_measure_labels.assert_called_once_with(x='a', y=2)

    @pytest.mark.asyncio
    async def test_measure_block_time__no_labels(self):
        delta = 0.1

        with capture_logs() as logs:
            with logger.measure_block_time("my_event"):
                await asyncio.sleep(delta)

        assert delta == pytest.approx(logs[0]['m_value'], 0.05)
        assert logs == [{'module': 'ffun.core.tests.test_logging', 'm_kind': 'measure', 'm_value': logs[0]['m_value'], 'event': 'my_event', 'log_level': 'info'}]

    @pytest.mark.asyncio
    async def test_measure_block_time__has_labels(self):
        delta = 0.1

        with capture_logs() as logs:
            with logger.measure_block_time("my_event", x="a", y=2):
                await asyncio.sleep(delta)
                assert_log_context_vars(m_labels={'x': 'a',
                                                  'y': 2})

        assert delta == pytest.approx(logs[0]['m_value'], 0.05)
        assert logs == [{'module': 'ffun.core.tests.test_logging', 'm_kind': 'measure', 'm_value': logs[0]['m_value'], 'event': 'my_event', 'log_level': 'info'}]

    @pytest.mark.asyncio
    async def test_measure_block_time__extra_labels(self, mocker: MockerFixture):
        delta = 0.1

        bound_measure_labels = mocker.patch('ffun.core.logging.bound_measure_labels')

        with capture_logs() as logs:
            with logger.measure_block_time("my_event", x="a", y=2) as extra_labels:
                await asyncio.sleep(delta)
                extra_labels['z'] = 3

        assert delta == pytest.approx(logs[0]['m_value'], 0.05)
        assert logs == [{'module': 'ffun.core.tests.test_logging', 'm_kind': 'measure', 'm_value': logs[0]['m_value'], 'event': 'my_event', 'log_level': 'info'}]

        bound_measure_labels.assert_has_calls([mock.call(x='a', y=2),
                                               mock.call(z=3)],
                                              any_order=True)
