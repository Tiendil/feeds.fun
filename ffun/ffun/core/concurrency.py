import asyncio
from collections.abc import Awaitable, Callable, Iterable
from typing import Generic, TypeVar, cast

from ffun.core import errors

ItemT = TypeVar("ItemT")
ResultT = TypeVar("ResultT")


class ConcurrentMapper(Generic[ItemT, ResultT]):
    __slots__ = ("_called", "_concurrency", "_handler", "_items")

    def __init__(
        self,
        items: Iterable[ItemT],
        handler: Callable[[ItemT], Awaitable[ResultT]],
        concurrency: int,
    ) -> None:
        if concurrency <= 0:
            raise errors.InvalidConcurrency()

        self._items = tuple(items)
        self._handler = handler
        self._concurrency = concurrency
        self._called = False

    async def __call__(self) -> list[ResultT]:
        if self._called:
            raise errors.ConcurrentMapperAlreadyCalled()

        self._called = True

        next_item_index = 0
        results: list[ResultT | None] = [None] * len(self._items)

        async def worker() -> None:
            nonlocal next_item_index

            while next_item_index < len(self._items):
                item_index = next_item_index
                next_item_index += 1
                results[item_index] = await self._handler(self._items[item_index])

        workers_number = min(self._concurrency, len(self._items))

        async with asyncio.TaskGroup() as task_group:
            for _ in range(workers_number):
                task_group.create_task(worker())

        return cast(list[ResultT], results)
