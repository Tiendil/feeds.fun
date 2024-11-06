import asyncio

import typer

from ffun.application.application import with_app
from ffun.core import logging
from ffun.ontology import domain as o_domain
from ffun.feeds import domain as f_domain
from ffun.library import domain as l_domain
from ffun.users import domain as u_domain
from ffun.scores import domain as s_domain
from ffun.feeds_links import domain as fl_domain
from ffun.resources import domain as r_domain

logger = logging.get_module_logger()

cli_app = typer.Typer()


async def system_slice_tags() -> None:
    tags_total = await o_domain.count_total_tags()

    logger.business_slice("tags_total", user_id=None, total=tags_total)

    tags_per_type = await o_domain.count_total_tags_per_type()

    logger.business_slice("tags_per_type", user_id=None, **{tag_type.name: count for tag_type, count in tags_per_type.items()})

    tags_per_category = await o_domain.count_total_tags_per_category()

    logger.business_slice("tags_per_category", user_id=None, **{tag_category.name: count for tag_category, count in tags_per_category.items()})


async def system_slice_feeds() -> None:
    feeds_total = await f_domain.count_total_feeds()

    logger.business_slice("feeds_total", user_id=None, total=feeds_total)

    feeds_per_state = await f_domain.count_total_feeds_per_state()

    logger.business_slice("feeds_per_state", user_id=None, **{feed_state.name: count for feed_state, count in feeds_per_state.items()})

    feeds_per_last_error = await f_domain.count_total_feeds_per_last_error()

    logger.business_slice("feeds_per_last_error", user_id=None, **{feed_error.name: count for feed_error, count in feeds_per_last_error.items()})


async def system_slice_entries() -> None:
    entries_total = await l_domain.count_total_entries()

    logger.business_slice("entries_total", user_id=None, total=entries_total)


async def system_slice_users() -> None:
    users_total = await u_domain.count_total_users()

    logger.business_slice("users_total", user_id=None, total=users_total)


async def run_system() -> None:

    metrics = {}

    async with with_app():
        await system_slice_tags()
        await system_slice_feeds()
        await system_slice_entries()
        await system_slice_users()


@cli_app.command()
def system() -> None:
    asyncio.run(run_system())


async def users_slice_rules() -> None:
    rules_per_user = await s_domain.count_rules_per_user()

    for user_id, count in rules_per_user.items():
        logger.business_slice("rules_per_user", user_id=user_id, total=count)


async def users_slice_feeds_links() -> None:
    feeds_per_user = await fl_domain.count_feeds_per_user()

    for user_id, count in feeds_per_user.items():
        logger.business_slice("feeds_per_user", user_id=user_id, total=count)

    collection_feeds_per_user = await fl_domain.count_collection_feeds_per_user()

    for user_id, count in collection_feeds_per_user.items():
        logger.business_slice("collection_feeds_per_user", user_id=user_id, total=count)


async def users_slice_resources() -> None:
    from ffun.application.resources import Resource

    users = {}

    resource_by_kind = {}

    for kind in Resource:
        resource_by_kind[kind] = await r_domain.count_total_resources_per_user(kind)

    for kind, resource_per_user in resource_by_kind.items():
        for user_id, count in resource_per_user.items():
            if user_id not in users:
                users[user_id] = {}

            users[user_id][kind.name] = count

    for user_id, resources in users.items():
        logger.business_slice("resources_per_user", user_id=user_id, **resources)


async def run_users() -> None:
    async with with_app():
        await users_slice_rules()
        await users_slice_feeds_links()
        await users_slice_resources()


@cli_app.command()
def users() -> None:
    asyncio.run(run_users())
