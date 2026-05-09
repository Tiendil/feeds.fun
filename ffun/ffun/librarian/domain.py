from ffun.core import logging, metrics
from ffun.core.postgresql import ExecuteType, run_in_transaction
from ffun.dispatcher import domain as d_domain
from ffun.domain.entities import ProcessorId
from ffun.librarian import errors, operations
from ffun.librarian.processors.base import Processor, ProcessorContext
from ffun.librarian.settings import settings
from ffun.library.entities import Entry
from ffun.ontology import domain as o_domain
from ffun.tags import domain as t_domain

logger = logging.get_module_logger()


count_failed_entries = operations.count_failed_entries


_processor_metrics_accumulators: dict[tuple[ProcessorId, str], metrics.Accumulator] = {}


# TODO: we may move metric accumulators to the processor info
def accumulator(event: str, processor_id: ProcessorId) -> metrics.Accumulator:
    key = (processor_id, event)

    if key in _processor_metrics_accumulators:
        return _processor_metrics_accumulators[key]

    accumulator = metrics.Accumulator(
        interval=settings.metric_accumulation_interval, event=event, processor_id=processor_id
    )

    _processor_metrics_accumulators[key] = accumulator

    return accumulator


@run_in_transaction
async def move_failed_entries_to_processor_queue(execute: ExecuteType, processor_id: ProcessorId, limit: int) -> None:
    failed_entries = await operations.get_failed_entries(execute, processor_id, limit)

    if not failed_entries:
        return

    await d_domain.push_entries_to_process(failed_entries, processor_id=processor_id)

    await operations.remove_failed_entries(execute, processor_id, failed_entries)


@logging.async_args_to_log("processor.name", "entry.id")
async def process_entry(
    processor_id: ProcessorId,
    processor: Processor,
    entry: Entry,
    context: ProcessorContext,
) -> None:
    logger.info("dicover_tags")

    raw_tags_metric = accumulator("processor_raw_tags", processor_id)
    normalized_tags_metric = accumulator("processor_normalized_tags", processor_id)

    try:
        raw_tags = await processor.process(entry, context=context)

        raw_tags_for_log = set(tag.raw_uid for tag in raw_tags)

        raw_tags_metric.measure(len(raw_tags))

        norm_tags = await t_domain.normalize(raw_tags)

        tags_for_log = {tag.uid for tag in norm_tags}

        logger.info(
            "tags_found",
            tags=sorted(tags_for_log),  # type: ignore
            lost=raw_tags_for_log - tags_for_log,
            added=tags_for_log - raw_tags_for_log,  # type: ignore
        )

        normalized_tags_metric.measure(len(norm_tags))

        await o_domain.apply_tags_to_entry(entry.id, processor_id, norm_tags)

        logger.info("processor_successed")
    except errors.SkipEntryProcessing as e:
        logger.warning("processor_requested_to_skip_entry", error_info=str(e))
    except errors.TemporaryErrorInProcessor as e:
        # log the error and move the entry to the failed storage
        # Note: it is a general plug, for some custom cases we may want to add custom processing
        # Note: currently, there are no logic to process failed storage, entries will just accumulate there
        logger.info("processor_temporary_error", error_info=str(e))
        await operations.add_entries_to_failed_storage(processor_id, [entry.id])
    except Exception as e:
        logger.exception("processor_failed")
        await operations.add_entries_to_failed_storage(processor_id, [entry.id])
        raise errors.UnexpectedErrorInProcessor(processor_id=processor_id, entry_id=str(entry.id)) from e
    finally:
        raw_tags_metric.flush_if_time()
        normalized_tags_metric.flush_if_time()

    logger.info("entry_processed")
