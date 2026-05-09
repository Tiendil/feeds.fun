import asyncio

from ffun.core import logging
from ffun.core.background_tasks import InfiniteTask
from ffun.dispatcher import domain as d_domain
from ffun.dispatcher.background_dispatcher import EntriesDispatcher
from ffun.dispatcher.entities import ProcessorDispatchInfo, ProcessorDispatchRoute
from ffun.domain.entities import EntryId
from ffun.librarian import domain
from ffun.librarian.entities import ProcessorType
from ffun.librarian.processors.base import Processor, ProcessorContext
from ffun.librarian.processors.domain import Processor as DomainProcessor
from ffun.librarian.processors.llm_general import Processor as LLMGeneralProcessor
from ffun.librarian.processors.native_tags import Processor as NativeTagsProcessor
from ffun.librarian.processors.upper_case_title import Processor as UpperCaseTitleProcessor
from ffun.librarian.settings import settings
from ffun.library import domain as l_domain
from ffun.library.entities import Entry

logger = logging.get_module_logger()


# TODO: merge with EntriesProcessor or with base.Processor?
class ProcessorInfo:
    __slots__ = (
        "id",
        "processor",
        "concurrency",
        "type",
        "routes",
    )

    def __init__(  # noqa: disable=CFQ002
        self,
        id: int,
        type: ProcessorType,
        processor: Processor,
        concurrency: int,
        routes: tuple[ProcessorDispatchRoute, ...],
    ):
        self.type = type
        self.id = id
        self.processor = processor
        self.concurrency = concurrency
        self.routes = routes

    def disptach_info(self) -> ProcessorDispatchInfo:
        return ProcessorDispatchInfo(
            processor_id=self.id,
            subqueue_id=self.id,
            routes=self.routes,
        )


processors: list[ProcessorInfo] = []


for processor_config in settings.tag_processors:
    if not processor_config.enabled:
        logger.info(
            "tag_processor_is_disabled", processor_id=processor_config.id, processor_name=processor_config.name
        )
        continue

    logger.info("add_tag_processor", processor_id=processor_config.id, processor_name=processor_config.name)

    info_arguments = {}

    tags_processor: Processor
    if processor_config.type == ProcessorType.domain:
        tags_processor = DomainProcessor(name=processor_config.name)
    elif processor_config.type == ProcessorType.native_tags:
        tags_processor = NativeTagsProcessor(name=processor_config.name)
    elif processor_config.type == ProcessorType.upper_case_title:
        tags_processor = UpperCaseTitleProcessor(name=processor_config.name)
    elif processor_config.type == ProcessorType.llm_general:
        tags_processor = LLMGeneralProcessor(
            name=processor_config.name,
            entry_template=processor_config.entry_template,
            text_cleaner=processor_config.text_cleaner,
            tag_extractor=processor_config.tags_extractor,
            llm_provider=processor_config.llm_provider,
            llm_config=processor_config.llm_config,
            collections_api_key=processor_config.collections_api_key,
            general_api_key=processor_config.general_api_key,
            max_tokens_per_entry=processor_config.max_tokens_per_entry,
            text_parts_intersection=processor_config.text_parts_intersection,
        )
    else:
        raise NotImplementedError(f"Unknown processor type: {processor_config.type}")

    info_arguments["processor"] = tags_processor

    processor = ProcessorInfo(
        id=processor_config.id,
        type=processor_config.type,
        processor=tags_processor,
        concurrency=processor_config.workers,
        routes=processor_config.dispatch_routes(),
    )

    processors.append(processor)


class EntriesProcessor(InfiniteTask):
    __slots__ = ("_processor_info",)

    def __init__(self, processor_info: ProcessorInfo, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore
        self._processor_info = processor_info

    @property
    def id(self) -> int:
        return self._processor_info.id

    @property
    def concurrency(self) -> int:
        return self._processor_info.concurrency

    async def separate_entries(  # noqa: disable=CCR001
        self, entries_ids: list[EntryId]
    ) -> tuple[list[Entry], list[EntryId]]:
        processor_id = self._processor_info.id

        # TODO: we could add caching here, because multiple processors can request the same entries
        #       and currently we run multiple processors in the same process
        #       but remember that for API worker such caching may be useless or even harmful
        entries = await l_domain.get_entries_by_ids(entries_ids)

        entries_to_process: list[Entry] = []
        entries_to_remove: list[EntryId] = []

        feed_links = await l_domain.get_feed_links_for_entries(entries_ids)
        feed_ids = {entry_id: [link.feed_id for link in links] for entry_id, links in feed_links.items()}

        for entry_id, entry in entries.items():
            if entry is None:
                logger.warning("unexisted_entry_in_queue", processor_id=processor_id, entry_id=entry_id)
                entries_to_remove.append(entry_id)
                continue

            if entry_id not in feed_ids:
                # this may happen when:
                # - we clean up DB from old data => drop linking, mark entries as orphaned
                # - but we still have these orphaned entries in the queues
                # - because the processor was stopped temporary or failed by other means
                logger.warning("entry_without_feeds_in_queue", processor_id=processor_id, entry_id=entry_id)
                entries_to_remove.append(entry_id)
                continue

            entries_to_process.append(entry)

        return entries_to_process, entries_to_remove

    async def single_run(self) -> None:
        processor_id = self._processor_info.id
        concurrency = self._processor_info.concurrency

        records = await d_domain.get_entries_to_tag(processor_id=processor_id, limit=concurrency)
        entries_ids = [record.item.entry_id for record in records]
        items_by_entry_id = {record.item.entry_id: record.item for record in records}

        if not entries_ids:
            logger.info("no_entries_to_process", processor_id=processor_id)
            return

        entries_to_process, entries_to_remove = await self.separate_entries(entries_ids=entries_ids)

        tasks = []

        for entry in entries_to_process:
            item = items_by_entry_id[entry.id]
            context = ProcessorContext(llm_api_key_type=item.llm_api_key_type)
            tasks.append(
                domain.process_entry(
                    processor_id=processor_id, processor=self._processor_info.processor, entry=entry, context=context
                )
            )

        await asyncio.gather(*tasks, return_exceptions=True)

        await d_domain.acknowledge([record.id for record in records if record.id is not None])


def create_background_processors() -> list[InfiniteTask]:
    if not processors:
        return []

    background_processors: list[InfiniteTask] = []

    background_processors.append(
        EntriesDispatcher(
            processors=[processor_info.disptach_info() for processor_info in processors],
            name="entries_dispatcher",
            delay_between_runs=1,
        )
    )

    for processor_info in processors:
        background_processors.append(
            EntriesProcessor(
                processor_info=processor_info,
                name=f"entries_processor_{processor_info.processor.name}",
                delay_between_runs=1,
            )
        )

    return background_processors
