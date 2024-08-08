import asyncio
import pathlib
import sys

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.processors_quality import domain as pq_domain
from ffun.processors_quality.entities import ProcessorResult
from ffun.processors_quality.knowlege_base import KnowlegeBase
from ffun.processors_quality.domain import diff_processor_results

logger = logging.get_module_logger()

cli_app = typer.Typer()


_root = pathlib.Path("./tags_quality_base/")


async def single_run(processor_name: str, entry_id: int, kb: KnowlegeBase, actual: bool = False) -> ProcessorResult:
    result = await pq_domain.run_processor(kb, processor_name, entry_id)
    kb.save_processor_result(processor_name, entry_id, result, actual=actual)
    return result


async def run_one(processor_name: str, entry_id: int, knowlege_root: pathlib.Path, actual: bool) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)

        r = await single_run(processor_name, entry_id, kb, actual=actual)

        # sys.stdout.write(f"must tags: {r.must_tags_number}/{r.must_tags_total}\n")
        # sys.stdout.write(f"must tags: {r.must_tags_found}\n")
        # sys.stdout.write(f"missing must tags: {r.must_tags_missing}\n")
        # sys.stdout.write("\n")
        # sys.stdout.write(f"should tags: {r.should_tags_number}/{r.should_tags_total}\n")
        # sys.stdout.write(f"should tags: {r.should_tags_found}\n")
        # sys.stdout.write(f"missing should tags: {r.should_tags_missing}\n")


@cli_app.command()
def test_one(processor: str, entry: int, knowlege_root: pathlib.Path = _root, actual: bool = False) -> None:
    asyncio.run(run_one(processor, entry, knowlege_root, actual=actual))


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


async def run_diff_entry(processor_name: str, entry_id: int, knowlege_root: pathlib.Path = _root) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)

        diffs = diff_processor_results(kb, processor_name, [entry_id])

        print(diffs)


@cli_app.command()
def diff_entry(processor: str, entry: int, knowlege_root: pathlib.Path = _root) -> None:
    asyncio.run(run_diff_entry(processor, entry, knowlege_root=knowlege_root))
