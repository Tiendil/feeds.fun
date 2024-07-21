import asyncio
from typing import Any

from ffun.core import logging
from ffun.core.background_tasks import InfiniteTask
from ffun.librarian import domain, operations
from ffun.librarian.processors.base import Processor
from ffun.librarian.processors.domain import Processor as DomainProcessor
from ffun.librarian.processors.native_tags import Processor as NativeTagsProcessor
from ffun.librarian.processors.openai_general import Processor as OpenGeneralProcessor
from ffun.librarian.processors.upper_case_title import Processor as UpperCaseTitleProcessor
from ffun.librarian.settings import settings
from ffun.library import domain as l_domain

logger = logging.get_module_logger()


class ProcessorInfo:
    __slots__ = ("_id", "_processor", "_concurrency")

    def __init__(self, id: int, processor: Processor, concurrency: int):
        self._id = id
        self._processor = processor
        self._concurrency = concurrency

    @property
    def id(self) -> int:
        return self._id

    @property
    def processor(self) -> Processor:
        return self._processor

    @property
    def concurrency(self) -> int:
        return self._concurrency


processors = []

if settings.domain_processor.enabled:
    processors.append(
        ProcessorInfo(id=1, processor=DomainProcessor(name="domain"), concurrency=settings.domain_processor.workers)
    )


if settings.native_tags_processor.enabled:
    processors.append(
        ProcessorInfo(
            id=2, processor=NativeTagsProcessor(name="native_tags"), concurrency=settings.native_tags_processor.workers
        )
    )


if settings.openai_general_processor.enabled:
    processors.append(
        ProcessorInfo(
            id=3,
            processor=OpenGeneralProcessor(name="openai_general", model=settings.openai_general_processor.model),
            concurrency=settings.openai_general_processor.workers,
        )
    )


# the processor 4 was "ChatGPT 3.5 + functions" and was removed in gh-227

if settings.upper_case_title_processor.enabled:
    processors.append(
        ProcessorInfo(
            id=5,
            processor=UpperCaseTitleProcessor(name="upper_case_title"),
            concurrency=settings.upper_case_title_processor.workers,
        )
    )


class EntriesProcessor(InfiniteTask):
    __slots__ = ("_processor_info",)

    def __init__(self, processor_info: ProcessorInfo, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._processor_info = processor_info

    @property
    def id(self) -> int:
        return self._processor_info.id

    @property
    def concurrency(self) -> int:
        return self._processor_info.concurrency

    async def single_run(self) -> None:
        processor_id = self._processor_info.id
        concurrency = self._processor_info.concurrency

        # most likely, this call should be in a separate worker with a more complex logic
        # but for now it is ok to place it here
        await domain.plan_processor_queue(
            processor_id=processor_id,
            fill_when_below=concurrency,
            # TODO: move to settings
            chunk=concurrency * 10,
        )

        entities_ids = await operations.get_entries_to_process(processor_id=processor_id, limit=concurrency)

        if not entities_ids:
            logger.info("no_entries_to_process", processor_id=processor_id)
            return

        # TODO: we could add caching here, because multiple processors can request the same entries
        #       and currently we run multiple processors in the same process
        #       but remember that for API worker such cachin may be useless or even harmful
        entries = await l_domain.get_entries_by_ids(entities_ids)

        tasks = []
        entries_to_remove = []

        for entry_id, entry in entries.items():
            if entry is None:
                entries_to_remove.append(entry_id)
                continue

            tasks.append(
                domain.process_entry(processor_id=processor_id, processor=self._processor_info.processor, entry=entry)
            )

        if entries_to_remove:
            logger.warning("unexisted_entries_in_queue", processor_id=processor_id, entries_ids=entries_to_remove)
            tasks.append(
                domain.remove_entries_from_processor_queue(processor_id=processor_id, entry_ids=entries_to_remove)
            )

        await asyncio.gather(*tasks, return_exceptions=True)


def create_background_processors() -> list[EntriesProcessor]:
    return [
        EntriesProcessor(
            processor_info=processor_info,
            name=f"entries_processor_{processor_info.processor.name}",
            delay_between_runs=1,
        )
        for processor_info in processors
    ]
