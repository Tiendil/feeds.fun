from collections.abc import Sequence

from ffun.core.background_tasks import InfiniteTask
from ffun.dispatcher import domain
from ffun.dispatcher.settings import settings


class EntriesDispatcher(InfiniteTask):
    __slots__ = ("_processor_ids", "_chunk")

    def __init__(self, processor_ids: Sequence[int], chunk: int | None = None, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore
        self._processor_ids = tuple(processor_ids)
        self._chunk = settings.dispatch_chunk if chunk is None else chunk

    async def single_run(self) -> None:
        await domain.dispatch_entries(processor_ids=self._processor_ids, limit=self._chunk)
