import asyncio

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.ontology import domain as o_domain

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def run_system() -> None:

    metrics = {}

    async with with_app():
        tags_total = await o_domain.count_total_tags()
        tags_per_type = await o_domain.count_total_tags_per_type()
        tags_per_category = await o_domain.count_total_tags_per_category()

        metrics["tags_total"] = tags_total

        for tag_type, count in tags_per_type.items():
            metrics[f"tags_type_{tag_type.name}"] = count

        for tag_category, count in tags_per_category.items():
            metrics[f"tags_category_{tag_category.name}"] = count

        # TOTAL feeds
        # TOTAL entries
        # TOTAL users

        logger.business_slice("system_metrics", user_id=None, **metrics)


@cli_app.command()
def system() -> None:
    asyncio.run(run_system())


async def run_per_user() -> None:
    async with with_app():
        # TODO: rules per user
        # TODO: feeds per user: custom, collections, total
        # TODO: has api key: yes/no, active/inactive
        # TODO: money spent
        pass


@cli_app.command()
def per_user() -> None:
    asyncio.run(run_per_user())
