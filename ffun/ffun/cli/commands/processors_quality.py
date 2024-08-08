import asyncio
import pathlib
import sys

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.processors_quality import domain as pq_domain
from ffun.processors_quality.entities import ProcessorResult
from ffun.processors_quality.knowlege_base import KnowlegeBase
from ffun.processors_quality.domain import diff_processor_results, display_diffs

logger = logging.get_module_logger()

cli_app = typer.Typer()


_root = pathlib.Path("./tags_quality_base/")


async def single_run(processor_name: str, entry_id: int, kb: KnowlegeBase, actual: bool = False) -> ProcessorResult:
    result = await pq_domain.run_processor(kb, processor_name, entry_id)
    kb.save_processor_result(processor_name, entry_id, result, actual=actual)
    return result


async def run_one(processor_name: str, entry_id: int, knowlege_root: pathlib.Path, actual: bool, show_tag_diffs: bool) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)

        await single_run(processor_name, entry_id, kb, actual=actual)

        diffs = diff_processor_results(kb, processor_name, [entry_id])

        display_diffs(diffs, show_tag_diffs=show_tag_diffs)


@cli_app.command()
def test_one(processor: str, entry: int, knowlege_root: pathlib.Path = _root, actual: bool = False, show_tag_diffs: bool = False) -> None:
    asyncio.run(run_one(processor, entry, knowlege_root, actual=actual, show_tag_diffs=show_tag_diffs))


async def run_all(processor_name: str, knowlege_root: pathlib.Path, actual: bool) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)

        ids = kb.entry_ids()

        for i, entry_id in enumerate(ids):
            logger.info("processing_entry", entry_id=entry_id, i=i, total=len(ids))
            await single_run(processor_name, entry_id, kb, actual=actual)


@cli_app.command()
def test_all(processor: str, knowlege_root: pathlib.Path = _root, actual: bool = False) -> None:
    asyncio.run(run_all(processor, knowlege_root, actual=actual))


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


async def run_diff_entry(processor_name: str, entry_id: int, show_tag_diffs: bool, knowlege_root: pathlib.Path = _root) -> None:
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
