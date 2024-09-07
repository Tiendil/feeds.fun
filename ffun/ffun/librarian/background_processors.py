import asyncio
import uuid
from typing import Any

from ffun.core import logging
from ffun.core.background_tasks import InfiniteTask
from ffun.librarian import domain, operations
from ffun.librarian.entities import ProcessorType
from ffun.librarian.processors.base import Processor
from ffun.librarian.processors.domain import Processor as DomainProcessor
from ffun.librarian.processors.llm_general import Processor as LLMGeneralProcessor
from ffun.librarian.processors.native_tags import Processor as NativeTagsProcessor
from ffun.librarian.processors.upper_case_title import Processor as UpperCaseTitleProcessor
from ffun.librarian.settings import settings
from ffun.library import domain as l_domain
from ffun.library.entities import Entry
from ffun.feeds_collections import domain as fc_domain

logger = logging.get_module_logger()


# TODO: merge with EntriesProcessor or with base.Processor?
class ProcessorInfo:
    __slots__ = ("id", "processor", "concurrency", "type", "allowed_for_collections", "allowed_for_users")

    def __init__(self,  # noqa: disable=CFQ002
                 id: int,
                 type: ProcessorType,
                 processor: Processor,
                 concurrency: int,
                 allowed_for_collections: bool,
                 allowed_for_users: bool):
        self.type = type
        self.id = id
        self.processor = processor
        self.concurrency = concurrency
        self.allowed_for_collections = allowed_for_collections
        self.allowed_for_users = allowed_for_users


processors: list[ProcessorInfo] = []


for processor_config in settings.tag_processors:
    if not processor_config.enabled:
        logger.info(
            "tag_processor_is_disabled", processor_id=processor_config.id, processor_name=processor_config.name
        )
        continue

    logger.info("add_tag_processor", processor_id=processor_config.id, processor_name=processor_config.name)

    info_arguments = {
        "id": processor_config.id,
        "type": processor_config.type,
        "concurrency": processor_config.workers,
        "allowed_for_collections": processor_config.allowed_for_collections,
        "allowed_for_users": processor_config.allowed_for_users,
    }

    if processor_config.type == ProcessorType.domain:
        processor = ProcessorInfo(
            processor=DomainProcessor(name=processor_config.name),
            **info_arguments,
        )
    elif processor_config.type == ProcessorType.native_tags:
        processor = ProcessorInfo(
            processor=NativeTagsProcessor(name=processor_config.name),
            **info_arguments,
        )
    elif processor_config.type == ProcessorType.upper_case_title:
        processor = ProcessorInfo(
            processor=UpperCaseTitleProcessor(name=processor_config.name),
            **info_arguments,
        )
    elif processor_config.type == ProcessorType.llm_general:
        processor = ProcessorInfo(
            processor=LLMGeneralProcessor(
                name=processor_config.name,
                entry_template=processor_config.entry_template,
                text_cleaner=processor_config.text_cleaner,
                tag_extractor=processor_config.tags_extractor,
                llm_provider=processor_config.llm_provider,
                llm_config=processor_config.llm_config,
                collections_api_key=processor_config.collections_api_key,
                general_api_key=processor_config.general_api_key,
            ),
            **info_arguments,
        )
    else:
        raise NotImplementedError(f"Unknown processor type: {processor_config.type}")

    processors.append(processor)


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

    # TODO: test
    async def separate_entries(self,  # noqa: disable=CCR001
                               entries_ids: list[uuid.UUID]) -> tuple[list[Entry], list[uuid.UUID]]:
        processor_id = self._processor_info.id

        # TODO: we could add caching here, because multiple processors can request the same entries
        #       and currently we run multiple processors in the same process
        #       but remember that for API worker such cachin may be useless or even harmful
        entries = await l_domain.get_entries_by_ids(entries_ids)

        entries_to_process: list[Entry] = []
        entries_to_remove: list[uuid.UUID] = []

        for entry_id, entry in entries.items():
            if entry is None:
                logger.warning("unexisted_entry_in_queue", processor_id=processor_id, entry_id=entry_id)
                entries_to_remove.append(entry_id)
                continue

            in_collection = await fc_domain.is_feed_in_collections(entry.feed_id)

            if in_collection and not self._processor_info.allowed_for_collections:
                logger.info("proccessor_not_allowed_for_collections", processor_id=processor_id, entry_id=entry_id)
                entries_to_remove.append(entry_id)
                continue

            if not in_collection and not self._processor_info.allowed_for_users:
                logger.info("proccessor_not_allowed_for_users", processor_id=processor_id, entry_id=entry_id)
                entries_to_remove.append(entry_id)
                continue

            logger.info("proccessor_is_allowed_for_entry", processor_id=processor_id, entry_id=entry_id)
            entries_to_process.append(entry)

        return entries_to_process, entries_to_remove

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

        entries_ids = await operations.get_entries_to_process(processor_id=processor_id, limit=concurrency)

        if not entries_ids:
            logger.info("no_entries_to_process", processor_id=processor_id)
            return

        entries_to_process, entries_to_remove = await self.separate_entries(entries_ids=entries_ids)

        tasks = []

        for entry in entries_to_process:
            tasks.append(
                domain.process_entry(processor_id=processor_id, processor=self._processor_info.processor, entry=entry)
            )

        if entries_to_remove:
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
