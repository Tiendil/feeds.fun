from collections.abc import Sequence

from ffun.core.background_tasks import InfiniteTask
from ffun.dispatcher import domain
from ffun.dispatcher.entities import ProcessorDispatchInfo
from ffun.dispatcher.settings import settings


class EntriesDispatcher(InfiniteTask):
    __slots__ = ("_batch_size", "_concurrency", "_processors")

    def __init__(
        self,
        processors: Sequence[ProcessorDispatchInfo],
        batch_size: int | None = None,
        concurrency: int | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)  # type: ignore
        self._processors = tuple(processors)
        self._batch_size = settings.dispatch_batch_size if batch_size is None else batch_size
        self._concurrency = settings.dispatch_concurrency if concurrency is None else concurrency

    async def single_run(self) -> None:
        await domain.dispatch_entries(
            processors=self._processors,
            batch_size=self._batch_size,
            concurrency=self._concurrency,
        )
