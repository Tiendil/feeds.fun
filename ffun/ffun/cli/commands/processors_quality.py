import asyncio
import uuid
import pathlib
import sys

import typer
from ffun.core import logging
from ffun.application.application import with_app

from ffun.processors_quality.knowlege_base import KnowlegeBase
from ffun.processors_quality import domain as pq_domain
from ffun.processors_quality.entities import ProcessorResult


logger = logging.get_module_logger()

cli_app = typer.Typer()


async def single_run(processor_name: str, entry_id: int, kb: KnowlegeBase, actual: bool = False) -> ProcessorResult:
    result = await pq_domain.run_processor(kb, processor_name, entry_id)
    kb.save_processor_result(processor_name, entry_id, result, actual=actual)
    return result


async def run_one(processor_name: str, entry_id: int, knowlege_root: pathlib.Path, actual: bool) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)

        r = await single_run(processor_name, entry_id, kb, actual=actual)

        print(f'must tags: {r.must_tags_number}/{r.must_tags_total}')
        print(f'must tags: {r.must_tags_found}')
        print(f'missing must tags: {r.must_tags_missing}')
        print()
        print(f'should tags: {r.should_tags_number}/{r.should_tags_total}')
        print(f'should tags: {r.should_tags_found}')
        print(f'missing should tags: {r.should_tags_missing}')


@cli_app.command()
def test_one(processor: str, entry: int, knowlege_root: pathlib.Path = pathlib.Path('./tags_quality_base/'), actual: bool = False) -> None:
    asyncio.run(run_one(processor, entry, knowlege_root, actual=actual))


async def run_all(processor_name: str, knowlege_root: pathlib.Path, actual: bool) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)

        ids = kb.entry_ids()

        for i, entry_id in enumerate(ids):
            logger.info('processing_entry', entry_id=entry_id, i=i, total=len(ids))
            await single_run(processor_name, entry_id, kb, actual=actual)


@cli_app.command()
def test_all(processor: str, knowlege_root: pathlib.Path = pathlib.Path('./tags_quality_base/'), actual: bool = False) -> None:
    asyncio.run(run_all(processor, knowlege_root, actual=actual))


async def run_validate_expected_tags(knowlege_root: pathlib.Path = pathlib.Path('./tags_quality_base/')) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)
        kb.validate_expected_tags()


@cli_app.command()
def validate_expected_tags(knowlege_root: pathlib.Path = pathlib.Path('./tags_quality_base/')) -> None:
    asyncio.run(run_validate_expected_tags(knowlege_root=knowlege_root))
