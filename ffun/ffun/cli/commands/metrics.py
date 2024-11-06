import asyncio

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.ontology import domain as o_domain
from ffun.feeds import domain as f_domain
from ffun.library import domain as l_domain
from ffun.users import domain as u_domain

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def slice_tags() -> None:
    tags_total = await o_domain.count_total_tags()

    logger.business_slice("tags_total", user_id=None, total=tags_total)

    tags_per_type = await o_domain.count_total_tags_per_type()

    logger.business_slice("tags_per_type", user_id=None, **{tag_type.name: count for tag_type, count in tags_per_type.items()})

    tags_per_category = await o_domain.count_total_tags_per_category()

    logger.business_slice("tags_per_category", user_id=None, **{tag_category.name: count for tag_category, count in tags_per_category.items()})


async def slice_feeds() -> None:
    feeds_total = await f_domain.count_total_feeds()

    logger.business_slice("feeds_total", user_id=None, total=feeds_total)

    feeds_per_state = await f_domain.count_total_feeds_per_state()

    logger.business_slice("feeds_per_state", user_id=None, **{feed_state.name: count for feed_state, count in feeds_per_state.items()})

    feeds_per_last_error = await f_domain.count_total_feeds_per_last_error()

    logger.business_slice("feeds_per_last_error", user_id=None, **{feed_error.name: count for feed_error, count in feeds_per_last_error.items()})


async def slice_entries() -> None:
    entries_total = await l_domain.count_total_entries()

    logger.business_slice("entries_total", user_id=None, total=entries_total)


async def slice_users() -> None:
    users_total = await u_domain.count_total_users()

    logger.business_slice("users_total", user_id=None, total=users_total)


async def run_system() -> None:

    metrics = {}

    async with with_app():
        await slice_tags()
        await slice_feeds()
        await slice_entries()
        await slice_users()


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
