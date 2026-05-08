from collections.abc import Sequence

from ffun.core.background_tasks import InfiniteTask
from ffun.dispatcher import domain
from ffun.dispatcher.entities import ProcessorDispatchInfo
from ffun.dispatcher.settings import settings


class EntriesDispatcher(InfiniteTask):
    __slots__ = ("_processors", "_chunk")

    def __init__(
        self, processors: Sequence[ProcessorDispatchInfo], chunk: int | None = None, **kwargs: object
    ) -> None:
        super().__init__(**kwargs)  # type: ignore
        self._processors = tuple(processors)
        self._chunk = settings.dispatch_chunk if chunk is None else chunk

    async def single_run(self) -> None:
        await domain.dispatch_entries(processors=self._processors, limit=self._chunk)
