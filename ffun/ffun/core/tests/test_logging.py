import asyncio

import pytest

from ffun.core import errors
from ffun.core.logging import (
    ArgumentConstructor,
    IdentityConstructor,
    bound_log_args,
    bound_measure_labels,
    function_args_to_log,
    get_module_logger,
)
from ffun.core.tests.helpers import assert_log_context_vars, capture_logs

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

        assert logs == [
            {
                "module": "ffun.core.tests.test_logging",
                "m_kind": "measure",
                "m_value": 42,
                "event": "my_event",
                "log_level": "info",
            }
        ]

    def test_measure__has_labels(self) -> None:
        with capture_logs() as logs:
            logger.measure("my_event", 42, x="a", y=2)

        assert logs == [
            {
                "module": "ffun.core.tests.test_logging",
                "m_kind": "measure",
                "m_value": 42,
                "event": "my_event",
                "log_level": "info",
                "m_labels": {"x": "a", "y": 2},
            }
        ]

    @pytest.mark.asyncio
    async def test_measure_block_time__no_labels(self) -> None:
        delta = 0.1

        with capture_logs() as logs:
            with logger.measure_block_time("my_event"):
                await asyncio.sleep(delta)

        assert delta == pytest.approx(logs[0]["m_value"], 0.05)
        assert logs == [
            {
                "module": "ffun.core.tests.test_logging",
                "m_kind": "measure",
                "m_value": logs[0]["m_value"],
                "event": "my_event",
                "log_level": "info",
            }
        ]

    @pytest.mark.asyncio
    async def test_measure_block_time__has_labels(self) -> None:
        delta = 0.1

        with capture_logs() as logs:
            with logger.measure_block_time("my_event", x="a", y=2):
                await asyncio.sleep(delta)
                assert_log_context_vars(m_labels={"x": "a", "y": 2})

        assert delta == pytest.approx(logs[0]["m_value"], 0.05)
        assert logs == [
            {
                "module": "ffun.core.tests.test_logging",
                "m_kind": "measure",
                "m_value": logs[0]["m_value"],
                "event": "my_event",
                "log_level": "info",
                "m_labels": {
                    "x": "a",
                    "y": 2,
                },
            }
        ]

    @pytest.mark.asyncio
    async def test_measure_block_time__extra_labels(self) -> None:
        delta = 0.1

        with capture_logs() as logs:
            with logger.measure_block_time("my_event", x="a", y=2) as extra_labels:
                await asyncio.sleep(delta)
                extra_labels["z"] = 3

        assert delta == pytest.approx(logs[0]["m_value"], 0.05)
        assert logs == [
            {
                "module": "ffun.core.tests.test_logging",
                "m_kind": "measure",
                "m_value": logs[0]["m_value"],
                "event": "my_event",
                "log_level": "info",
                "m_labels": {"x": "a", "y": 2, "z": 3},
            }
        ]


class TestIdentityConstructor:

    def test_init(self) -> None:
        constructor = IdentityConstructor("name")

        assert constructor.name == "name"

    def test_works(self) -> None:
        constructor = IdentityConstructor("name")

        assert constructor({"name": "value"}) == "value"

    def test_no_argument(self) -> None:
        constructor = IdentityConstructor("name")

        assert constructor({"bad_name": "value"}) is None


class TestArgumentConstructor:

    def test_init(self) -> None:
        constructor = ArgumentConstructor("x.my_arg")

        assert constructor.name == "x_my_arg"
        assert constructor.key == "x"
        assert constructor.attribute == "my_arg"

    def test_works(self) -> None:
        constructor = ArgumentConstructor("x.my_arg")

        assert constructor({"x": X("abc")}) == "abc"

    def test_no_argument(self) -> None:
        constructor = ArgumentConstructor("x.my_arg")

        assert constructor({"bad_name": "value"}) is None

    def test_no_attribute(self) -> None:
        constructor = ArgumentConstructor("x.wrong_arg")

        assert constructor({"x": X("abc")}) is None


class TestFunctionArgsToLog:

    def test_sync(self) -> None:

        @function_args_to_log("y", "x.my_arg")
        def func(y: int, x: X, z: int) -> None:
            logger.info("my_event")
            assert_log_context_vars(y=1, x_my_arg="abc")

        with capture_logs() as logs:
            func(y=1, x=X("abc"), z=2)

        assert logs == [
            {
                "module": "ffun.core.tests.test_logging",
                "event": "my_event",
                "log_level": "info",
                "x_my_arg": "abc",
                "y": 1,
            }
        ]

    @pytest.mark.asyncio
    async def test_async(self) -> None:

        @function_args_to_log("y", "x.my_arg")
        async def func(y: int, x: X, z: int) -> None:
            await asyncio.sleep(0)
            logger.info("my_event")
            assert_log_context_vars(y=1, x_my_arg="abc")

        with capture_logs() as logs:
            await func(y=1, x=X("abc"), z=2)

        assert logs == [
            {
                "module": "ffun.core.tests.test_logging",
                "event": "my_event",
                "log_level": "info",
                "x_my_arg": "abc",
                "y": 1,
            }
        ]


class TestBoundLogArgs:

    def test_no_args(self) -> None:
        with capture_logs() as logs:
            with bound_log_args():
                logger.info("my_event", a="b")
                logger.measure("my_event", 42, z=3)
                assert_log_context_vars()

        assert logs == [
            {"module": "ffun.core.tests.test_logging", "event": "my_event", "log_level": "info", "a": "b"},
            {
                "module": "ffun.core.tests.test_logging",
                "m_kind": "measure",
                "m_value": 42,
                "event": "my_event",
                "log_level": "info",
                "m_labels": {"z": 3},
            },
        ]

    def test_with_args(self) -> None:
        with capture_logs() as logs:
            with bound_log_args(x=1, y="a"):
                logger.info("my_event", a="b")
                logger.measure("my_event", 42, z=3)
                assert_log_context_vars(x=1, y="a")

        assert logs == [
            {
                "module": "ffun.core.tests.test_logging",
                "event": "my_event",
                "log_level": "info",
                "a": "b",
                "x": 1,
                "y": "a",
            },
            {
                "module": "ffun.core.tests.test_logging",
                "m_kind": "measure",
                "m_value": 42,
                "event": "my_event",
                "log_level": "info",
                "x": 1,
                "y": "a",
                "m_labels": {"z": 3},
            },
        ]

    @pytest.mark.parametrize("protected", ["m_labels", "m_value", "m_kind"])
    def test_reserved(self, protected: str) -> None:
        with pytest.raises(errors.ReservedLogArguments):
            with bound_log_args(**{protected: 1}):
                pass

    def test_recursive(self) -> None:
        with capture_logs() as logs:
            with bound_log_args(x=1):
                with bound_log_args(y=2):
                    logger.info("my_event", a="b")
                    logger.measure("my_event", 42, z=3)
                    assert_log_context_vars(x=1, y=2)

                logger.info("my_event_2", a="c")
                logger.measure("my_event_2", 43, z=4)

                assert_log_context_vars(x=1)

            assert_log_context_vars()

        assert logs == [
            {
                "module": "ffun.core.tests.test_logging",
                "event": "my_event",
                "log_level": "info",
                "a": "b",
                "x": 1,
                "y": 2,
            },
            {
                "module": "ffun.core.tests.test_logging",
                "m_kind": "measure",
                "m_value": 42,
                "event": "my_event",
                "log_level": "info",
                "x": 1,
                "y": 2,
                "m_labels": {"z": 3},
            },
            {"module": "ffun.core.tests.test_logging", "event": "my_event_2", "log_level": "info", "a": "c", "x": 1},
            {
                "module": "ffun.core.tests.test_logging",
                "m_kind": "measure",
                "m_value": 43,
                "event": "my_event_2",
                "log_level": "info",
                "x": 1,
                "m_labels": {"z": 4},
            },
        ]

    def test_duplicated_args(self) -> None:
        with pytest.raises(errors.DuplicatedLogArguments):
            with bound_log_args(x=1):
                with bound_log_args(x=2):
                    pass


class TestBoundMeasureLabels:

    def test_no_labels(self) -> None:
        with capture_logs() as logs:
            with bound_measure_labels():
                logger.info("my_event", a="b")
                logger.measure("my_event", 42, z=3)
                assert_log_context_vars()

        assert logs == [
            {"module": "ffun.core.tests.test_logging", "event": "my_event", "log_level": "info", "a": "b"},
            {
                "module": "ffun.core.tests.test_logging",
                "m_kind": "measure",
                "m_value": 42,
                "event": "my_event",
                "log_level": "info",
                "m_labels": {"z": 3},
            },
        ]

    def test_with_labels(self) -> None:
        with capture_logs() as logs:
            with bound_measure_labels(x=1, y="a"):
                logger.info("my_event", a="b")
                logger.measure("my_event", 42, z=3)
                assert_log_context_vars(m_labels={"x": 1, "y": "a"})

        assert logs == [
            {
                "module": "ffun.core.tests.test_logging",
                "event": "my_event",
                "log_level": "info",
                "a": "b",
                "m_labels": {"x": 1, "y": "a"},
            },
            {
                "module": "ffun.core.tests.test_logging",
                "m_kind": "measure",
                "m_value": 42,
                "event": "my_event",
                "log_level": "info",
                "m_labels": {"x": 1, "y": "a", "z": 3},
            },
        ]

    def test_recursive(self) -> None:
        with capture_logs() as logs:
            with bound_measure_labels(x=1):
                assert_log_context_vars(m_labels={"x": 1})

                with bound_measure_labels(y=2):
                    logger.info("my_event", a="b")
                    logger.measure("my_event", 42, z=3)
                    assert_log_context_vars(m_labels={"x": 1, "y": 2})

                logger.info("my_event_2", a="c")
                logger.measure("my_event_2", 43, z=4)

                assert_log_context_vars(m_labels={"x": 1})

            assert_log_context_vars()

        assert logs == [
            {
                "module": "ffun.core.tests.test_logging",
                "event": "my_event",
                "log_level": "info",
                "a": "b",
                "m_labels": {"x": 1, "y": 2},
            },
            {
                "module": "ffun.core.tests.test_logging",
                "m_kind": "measure",
                "m_value": 42,
                "event": "my_event",
                "log_level": "info",
                "m_labels": {"x": 1, "y": 2, "z": 3},
            },
            {
                "module": "ffun.core.tests.test_logging",
                "event": "my_event_2",
                "log_level": "info",
                "a": "c",
                "m_labels": {"x": 1},
            },
            {
                "module": "ffun.core.tests.test_logging",
                "m_kind": "measure",
                "m_value": 43,
                "event": "my_event_2",
                "log_level": "info",
                "m_labels": {"x": 1, "z": 4},
            },
        ]

    def test_duplicated_labels(self) -> None:
        with pytest.raises(errors.DuplicatedMeasureLabels):
            with bound_measure_labels(x=1):
                with bound_measure_labels(x=2):
                    pass
