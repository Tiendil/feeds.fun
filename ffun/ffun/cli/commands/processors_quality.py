import asyncio
import pathlib
from collections import Counter

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.processors_quality import domain as pq_domain
from ffun.processors_quality.domain import diff_processor_results, display_diffs
from ffun.processors_quality.entities import ProcessorResult
from ffun.processors_quality.knowlege_base import KnowlegeBase

logger = logging.get_module_logger()

cli_app = typer.Typer()


_root = pathlib.Path("./tags_quality_base/")


async def single_run(processor_name: str, entry_id: int, kb: KnowlegeBase, actual: bool = False) -> ProcessorResult:
    logger.info("processing_entry", entry_id=entry_id)
    result = await pq_domain.run_processor(kb, processor_name, entry_id)
    kb.save_processor_result(processor_name, entry_id, result, actual=actual)
    return result


async def run_one(
    processor_name: str, entry_id: int, knowlege_root: pathlib.Path, actual: bool, show_tag_diffs: bool
) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)

        await single_run(processor_name, entry_id, kb, actual=actual)

        diffs = diff_processor_results(kb, processor_name, [entry_id])

        display_diffs(diffs, show_tag_diffs=show_tag_diffs)


@cli_app.command()
def test_one(
    processor: str, entry: int, knowlege_root: pathlib.Path = _root, actual: bool = False, show_tag_diffs: bool = False
) -> None:
    asyncio.run(run_one(processor, entry, knowlege_root, actual=actual, show_tag_diffs=show_tag_diffs))


async def run_all(processor_name: str, knowlege_root: pathlib.Path, actual: bool, show_tag_diffs: bool) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)

        ids = kb.entry_ids()

        tasks = []

        for entry_id in ids:
            tasks.append(single_run(processor_name, entry_id, kb, actual=actual))

        await asyncio.gather(*tasks)

        diffs = diff_processor_results(kb, processor_name, ids)

        display_diffs(diffs, show_tag_diffs=show_tag_diffs)


@cli_app.command()
def test_all(
    processor: str, knowlege_root: pathlib.Path = _root, actual: bool = False, show_tag_diffs: bool = False
) -> None:
    asyncio.run(run_all(processor, knowlege_root, actual=actual, show_tag_diffs=show_tag_diffs))


async def run_validate_expected_tags(knowlege_root: pathlib.Path = _root) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)
        kb.validate_expected_tags()


@cli_app.command()
def validate_expected_tags(knowlege_root: pathlib.Path = _root) -> None:
    asyncio.run(run_validate_expected_tags(knowlege_root=knowlege_root))


async def run_copy_last_to_actual(processor: str, entry: int, knowlege_root: pathlib.Path = _root) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)
        kb.copy_last_to_actual(processor, entry)


@cli_app.command()
def copy_last_to_actual(processor: str, entry: int, knowlege_root: pathlib.Path = _root) -> None:
    asyncio.run(run_copy_last_to_actual(processor, entry, knowlege_root=knowlege_root))


async def run_copy_last_to_actual_all(processor: str, knowlege_root: pathlib.Path = _root) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)
        ids = kb.entry_ids()

        for i, entry_id in enumerate(ids):
            logger.info("copying_last_to_actual", entry_id=entry_id, i=i, total=len(ids))
            kb.copy_last_to_actual(processor, entry_id)


@cli_app.command()
def copy_last_to_actual_all(processor: str, knowlege_root: pathlib.Path = _root) -> None:
    asyncio.run(run_copy_last_to_actual_all(processor, knowlege_root=knowlege_root))


async def run_diff_entry(
    processor_name: str, entry_id: int, show_tag_diffs: bool, knowlege_root: pathlib.Path = _root
) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)

        diffs = diff_processor_results(kb, processor_name, [entry_id])

        display_diffs(diffs, show_tag_diffs=show_tag_diffs)


@cli_app.command()
def diff_entry(processor: str, entry: int, knowlege_root: pathlib.Path = _root, show_tag_diffs: bool = False) -> None:
    asyncio.run(run_diff_entry(processor, entry, knowlege_root=knowlege_root, show_tag_diffs=show_tag_diffs))


async def run_deff_all(processor_name: str, knowlege_root: pathlib.Path = _root, show_tag_diffs: bool = False) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)

        diffs = diff_processor_results(kb, processor_name, kb.entry_ids())

        display_diffs(diffs, show_tag_diffs)


@cli_app.command()
def diff_all(processor: str, knowlege_root: pathlib.Path = _root, show_tag_diffs: bool = False) -> None:
    asyncio.run(run_deff_all(processor, knowlege_root=knowlege_root, show_tag_diffs=show_tag_diffs))


async def run_prepare_news_item(
    processor: str, entry_id: int, knowlege_root: pathlib.Path, requests_number: int, min_tags_count: int
) -> None:
    results = []

    async with with_app():
        kb = KnowlegeBase(knowlege_root)

        for i in range(requests_number):
            logger.info("requesting_tags", step=i, steps_number=requests_number)
            result = await single_run(processor, entry_id, kb, actual=True)
            results.append(result)

        logger.info("requests_completed")

        tags: Counter[str] = Counter()

        for result in results:
            tags.update(result.tags)

        tags_must_have = {tag for tag, count in tags.items() if count == requests_number}
        tags_should_have = {tag for tag, count in tags.items() if min_tags_count <= count < requests_number}

        kb.save_expected_data(processor, entry_id, tags_must_have=tags_must_have, tags_should_have=tags_should_have)


@cli_app.command()
def prepere_news_item(
    processor: str, entry: int, knowlege_root: pathlib.Path = _root, requests_number: int = 10, min_tags_count: int = 5
) -> None:
    asyncio.run(
        run_prepare_news_item(
            processor,
            entry_id=entry,
            knowlege_root=knowlege_root,
            requests_number=requests_number,
            min_tags_count=min_tags_count,
        )
    )
