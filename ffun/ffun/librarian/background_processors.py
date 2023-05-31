import asyncio

from ffun.core import logging
from ffun.core.background_tasks import InfiniteTask
from ffun.library import domain as l_domain

from . import domain
from .processors.base import Processor
from .processors.domain import Processor as DomainProcessor
from .processors.native_tags import Processor as NativeTagsProcessor
from .processors.openai_chat_3_5 import Processor as OpenAIChat35Processor
from .settings import settings

logger = logging.get_module_logger()


class ProcessorInfo:
    __slots__ = ('_id', '_processor', '_concurrency')

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


processors = [ProcessorInfo(id=1, processor=DomainProcessor(name='domain'), concurrency=1),
              ProcessorInfo(id=2, processor=NativeTagsProcessor(name='native_tags'), concurrency=1)]

if settings.openai.enabled:
    processors.append(ProcessorInfo(id=3, processor=OpenAIChat35Processor(name='openai_chat_3_5'), concurrency=15))


class EntriesProcessor(InfiniteTask):
    __slots__ = ('_processor_info',)

    def __init__(self, processor_info: ProcessorInfo, **kwargs) -> None:
        super().__init__(**kwargs)
        self._processor_info = processor_info

    async def single_run(self) -> None:
        processor_id = self._processor_info.id
        concurrency = self._processor_info.concurrency

        entries = await l_domain.get_entries_to_process(processor_id=processor_id,
                                                        number=concurrency)

        tasks = [domain.process_entry(processor_id=processor_id,
                                      processor=self._processor_info.processor,
                                      entry=entry) for entry in entries]

        await asyncio.gather(*tasks, return_exceptions=True)


def create_background_processors() -> list[EntriesProcessor]:
    return [EntriesProcessor(processor_info=processor_info,
                             name=f'entries_processor_{processor_info.processor.name}',
                             delay_between_runs=1)
            for processor_info in processors]
