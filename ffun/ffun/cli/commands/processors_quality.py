import asyncio
import uuid
import pathlib

import typer

from ffun.application.application import with_app
from ffun.core import logging


from ffun.processors_quality.knowlege_base import KnowlegeBase
from ffun.processors_quality import domain as pq_domain


logger = logging.get_module_logger()

cli_app = typer.Typer()


async def run(processor_name: str, entry_id: int, knowlege_root: pathlib.Path) -> None:
    async with with_app():
        kb = KnowlegeBase(knowlege_root)

        r = await pq_domain.run_processor(kb, processor_name, entry_id)

        print(f'must tags: {r.must_tags_number}/{r.must_tags_total}')
        print(f'must tags: {r.must_tags_found}')
        print(f'missing must tags: {r.must_tags_missing}')
        print()
        print(f'should tags: {r.should_tags_number}/{r.should_tags_total}')
        print(f'should tags: {r.should_tags_found}')
        print(f'missing should tags: {r.should_tags_missing}')


@cli_app.command()
def test(processor: str, entry: int, knowlege_root: pathlib.Path = pathlib.Path('./tags_quality_base/')) -> None:
    asyncio.run(run(processor, entry, knowlege_root))
