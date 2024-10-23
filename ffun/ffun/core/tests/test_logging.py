
import asyncio
import pytest
from unittest import mock
from pytest_mock import MockerFixture
from structlog.testing import capture_logs
from structlog import contextvars as structlog_contextvars
from ffun.core import errors
from ffun.core.logging import MeasuringBoundLoggerMixin, get_module_logger, IdentityConstructor, ArgumentConstructor, function_args_to_log, bound_log_args, bound_measure_labels
from ffun.core.tests.helpers import assert_logs, assert_logs_levels, assert_log_context_vars


logger = get_module_logger()


class X:
    def __init__(self, my_arg: str) -> None:
        self.my_arg = my_arg


class TestMeasuringBoundLoggerMixin:
    """Test mixin methods after they applied to the logger class.

    Because it is more convinient, rather than testing the mixin itself.

    ATTENTION: `capture_logs` does not apply processorts => does not merge `m_labels`
               => we test them separately where it is possible
    """

    def test_measure__no_labels(self) -> None:
        with capture_logs() as logs:
            logger.measure("my_event", 42)
            assert_log_context_vars()

        assert logs == [{'module': 'ffun.core.tests.test_logging', 'm_kind': 'measure', 'm_value': 42, 'event': 'my_event', 'log_level': 'info'}]

    def test_measure__has_labels(self, mocker: MockerFixture) -> None:
        bound_measure_labels = mocker.patch('ffun.core.logging.bound_measure_labels')

        with capture_logs() as logs:
            logger.measure("my_event", 42, x="a", y=2)

        assert logs == [{'module': 'ffun.core.tests.test_logging', 'm_kind': 'measure', 'm_value': 42, 'event': 'my_event', 'log_level': 'info'}]

        bound_measure_labels.assert_called_once_with(x='a', y=2)

    @pytest.mark.asyncio
    async def test_measure_block_time__no_labels(self) -> None:
        delta = 0.1

        with capture_logs() as logs:
            with logger.measure_block_time("my_event"):
                await asyncio.sleep(delta)

        assert delta == pytest.approx(logs[0]['m_value'], 0.05)
        assert logs == [{'module': 'ffun.core.tests.test_logging', 'm_kind': 'measure', 'm_value': logs[0]['m_value'], 'event': 'my_event', 'log_level': 'info'}]

    @pytest.mark.asyncio
    async def test_measure_block_time__has_labels(self) -> None:
        delta = 0.1

        with capture_logs() as logs:
            with logger.measure_block_time("my_event", x="a", y=2):
                await asyncio.sleep(delta)
                assert_log_context_vars(m_labels={'x': 'a',
                                                  'y': 2})

        assert delta == pytest.approx(logs[0]['m_value'], 0.05)
        assert logs == [{'module': 'ffun.core.tests.test_logging', 'm_kind': 'measure', 'm_value': logs[0]['m_value'], 'event': 'my_event', 'log_level': 'info'}]

    @pytest.mark.asyncio
    async def test_measure_block_time__extra_labels(self, mocker: MockerFixture) -> None:
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


class TestIdentityConstructor:

    def test_init(self) -> None:
        constructor = IdentityConstructor('name')

        assert constructor.name == 'name'

    def test_works(self) -> None:
        constructor = IdentityConstructor('name')

        assert constructor({'name': 'value'}) == 'value'

    def test_no_argument(self) -> None:
        constructor = IdentityConstructor('name')

        assert constructor({'bad_name': 'value'}) is None


class TestArgumentConstructor:

    def test_init(self) -> None:
        constructor = ArgumentConstructor('x.my_arg')

        assert constructor.name == 'x_my_arg'
        assert constructor.key == 'x'
        assert constructor.attribute == 'my_arg'

    def test_works(self) -> None:
        constructor = ArgumentConstructor('x.my_arg')

        assert constructor({'x': X('abc')}) == 'abc'

    def test_no_argument(self) -> None:
        constructor = ArgumentConstructor('x.my_arg')

        assert constructor({'bad_name': 'value'}) is None

    def test_no_attribute(self) -> None:
        constructor = ArgumentConstructor('x.wrong_arg')

        assert constructor({'x': X('abc')}) is None


class TestFunctionArgsToLog:

    def test_sync(self) -> None:

        @function_args_to_log('y', 'x.my_arg')
        def func(y: int, x: X, z: int) -> None:
            logger.info('my_event')
            assert_log_context_vars(y=1, x_my_arg='abc')

        with capture_logs() as logs:
            func(y=1, x=X('abc'), z=2)

        assert logs == [{'module': 'ffun.core.tests.test_logging', 'event': 'my_event', 'log_level': 'info'}]

    @pytest.mark.asyncio
    async def test_async(self) -> None:

        @function_args_to_log('y', 'x.my_arg')
        async def func(y: int, x: X, z: int) -> None:
            await asyncio.sleep(0)
            logger.info('my_event')
            assert_log_context_vars(y=1, x_my_arg='abc')

        with capture_logs() as logs:
            await func(y=1, x=X('abc'), z=2)

        assert logs == [{'module': 'ffun.core.tests.test_logging', 'event': 'my_event', 'log_level': 'info'}]


class TestBoundLogArgs:

    def test_no_args(self) -> None:
        with bound_log_args():
            assert_log_context_vars()

    def test_with_args(self) -> None:
        with bound_log_args(x=1, y='a'):
            assert_log_context_vars(x=1, y='a')

    @pytest.mark.parametrize('protected', ['m_labels', 'm_value', 'm_kind'])
    def test_reserved(self, protected: str) -> None:
        with pytest.raises(errors.ReservedLogArguments):
            with bound_log_args(**{protected: 1}):
                pass

    def test_recursive(self) -> None:
        with bound_log_args(x=1):
            with bound_log_args(y=2):
                assert_log_context_vars(x=1, y=2)

            assert_log_context_vars(x=1)

        assert_log_context_vars()

    def test_duplicated_args(self) -> None:
        with pytest.raises(errors.DuplicatedLogArguments):
            with bound_log_args(x=1):
                with bound_log_args(x=2):
                    pass


class TestBoundMeasureLabels:

    def test_no_labels(self) -> None:
        with bound_measure_labels():
            assert_log_context_vars()

    def test_with_labels(self) -> None:
        with bound_measure_labels(x=1, y='a'):
            assert_log_context_vars(m_labels={'x': 1, 'y': 'a'})

    def test_recursive(self) -> None:
        with bound_measure_labels(x=1):
            assert_log_context_vars(m_labels={'x': 1})

            with bound_measure_labels(y=2):
                assert_log_context_vars(m_labels={'x': 1, 'y': 2})

            assert_log_context_vars(m_labels={'x': 1})

        assert_log_context_vars()

    def test_duplicated_labels(self) -> None:
        with pytest.raises(errors.DuplicatedMeasureLabels):
            with bound_measure_labels(x=1):
                with bound_measure_labels(x=2):
                    pass
