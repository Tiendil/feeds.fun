import asyncio

import pytest

from ffun.core import errors
from ffun.core.concurrency import ConcurrentMapper


async def identity(value: int) -> int:
    return value


class TestConcurrentMapper:
    @pytest.mark.parametrize("concurrency", [0, -1])
    def test_init__non_positive_concurrency(self, concurrency: int) -> None:
        with pytest.raises(errors.InvalidConcurrency):
            ConcurrentMapper(items=[1], handler=identity, concurrency=concurrency)

    @pytest.mark.asyncio
    async def test_call__empty_items(self) -> None:
        results = await ConcurrentMapper(items=[], handler=identity, concurrency=2)()

        assert results == []

    @pytest.mark.asyncio
    async def test_call__preserves_item_order(self) -> None:
        async def handler(value: int) -> int:
            await asyncio.sleep((3 - value) * 0.001)
            return value

        results = await ConcurrentMapper(items=[1, 2, 3], handler=handler, concurrency=3)()

        assert results == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_call__limits_concurrency(self) -> None:
        active_tasks = 0
        max_active_tasks = 0

        async def handler(value: int) -> int:
            nonlocal active_tasks, max_active_tasks

            active_tasks += 1
            max_active_tasks = max(max_active_tasks, active_tasks)
            await asyncio.sleep(0)
            active_tasks -= 1

            return value

        results = await ConcurrentMapper(items=range(5), handler=handler, concurrency=2)()

        assert results == list(range(5))
        assert max_active_tasks == 2

    @pytest.mark.asyncio
    async def test_call__handler_failure(self) -> None:
        async def handler(value: int) -> int:
            if value == 1:
                raise RuntimeError("test error")

            await asyncio.sleep(10)
            return value

        with pytest.raises(ExceptionGroup) as exception_info:
            await ConcurrentMapper(items=[0, 1], handler=handler, concurrency=2)()

        assert len(exception_info.value.exceptions) == 1
        assert isinstance(exception_info.value.exceptions[0], RuntimeError)

    @pytest.mark.asyncio
    async def test_call__second_call(self) -> None:
        mapper = ConcurrentMapper(items=[1, 2, 3], handler=identity, concurrency=2)

        assert await mapper() == [1, 2, 3]

        with pytest.raises(errors.ConcurrentMapperAlreadyCalled):
            await mapper()

    @pytest.mark.asyncio
    async def test_call__after_handler_failure(self) -> None:
        async def handler(value: int) -> int:
            raise RuntimeError(value)

        mapper = ConcurrentMapper(items=[1], handler=handler, concurrency=1)

        with pytest.raises(ExceptionGroup):
            await mapper()

        with pytest.raises(errors.ConcurrentMapperAlreadyCalled):
            await mapper()
