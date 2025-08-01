import asyncio
import datetime
import uuid

import typer

from ffun.application.application import with_app
from ffun.core import logging, utils
from ffun.domain.entities import CollectionId, FeedId, UserId
from ffun.feeds import domain as f_domain
from ffun.feeds_collections.collections import collections
from ffun.feeds_links import domain as fl_domain
from ffun.librarian import background_processors
from ffun.librarian import domain as ln_domain
from ffun.library import domain as l_domain
from ffun.ontology import domain as o_domain
from ffun.resources import domain as r_domain
from ffun.scores import domain as s_domain
from ffun.users import domain as u_domain

logger = logging.get_module_logger()

cli_app = typer.Typer()

################
# System metrics
################


async def system_slice_tags() -> None:
    tags_total = await o_domain.count_total_tags()

    logger.business_slice("tags_total", user_id=None, total=tags_total)

    tags_per_type = await o_domain.count_total_tags_per_type()

    logger.business_slice(
        "tags_per_type", user_id=None, **{tag_type.name: count for tag_type, count in tags_per_type.items()}
    )

    tags_per_category = await o_domain.count_total_tags_per_category()

    logger.business_slice(
        "tags_per_category",
        user_id=None,
        **{tag_category.name: count for tag_category, count in tags_per_category.items()},
    )


async def _system_slice_new_tags_count(date: datetime.date) -> None:
    count = await o_domain.count_new_tags_at(date)

    logger.business_slice("new_tags_count", user_id=None, date=date.isoformat(), count=count)


# We count new tags for yesterday to ensure that
# we'll count all tags created from the last envocation of this function and the midnight.
async def system_slice_new_tags_count() -> None:
    today = utils.now().date()

    await _system_slice_new_tags_count(today)
    await _system_slice_new_tags_count(today - datetime.timedelta(days=1))


async def system_slice_tag_frequencies() -> None:
    buckets = [
        1,
        2,
        3,
        4,
        5,
        6,
        7,
        8,
        9,
        10,
        20,
        30,
        40,
        50,
        60,
        70,
        80,
        90,
        100,
        200,
        300,
        400,
        500,
        600,
        700,
        800,
        900,
        1000,
        2000,
        3000,
        4000,
        5000,
        6000,
        7000,
        8000,
        9000,
        10000,
        20000,
        30000,
        40000,
        50000,
        60000,
        70000,
        80000,
        90000,
        100000,
        200000,
        300000,
        400000,
        500000,
        600000,
        700000,
        800000,
        900000,
    ]

    stats = await o_domain.tag_frequency_statistics(buckets)

    logger.business_slice(
        "tag_frequency",
        user_id=None,
        **{f"b{i:02d}_{b.lower_bound}_{b.upper_bound}": b.count for i, b in enumerate(stats)},
    )


async def system_slice_feeds() -> None:
    feeds_total = await f_domain.count_total_feeds()

    logger.business_slice("feeds_total", user_id=None, total=feeds_total)

    feeds_per_state = await f_domain.count_total_feeds_per_state()

    logger.business_slice(
        "feeds_per_state", user_id=None, **{feed_state.name: count for feed_state, count in feeds_per_state.items()}
    )

    feeds_per_last_error = await f_domain.count_total_feeds_per_last_error()

    logger.business_slice(
        "feeds_per_last_error",
        user_id=None,
        **{feed_error.name: count for feed_error, count in feeds_per_last_error.items()},
    )


async def system_slice_entries() -> None:
    entries_total = await l_domain.count_total_entries()

    logger.business_slice("entries_total", user_id=None, total=entries_total)


async def system_slice_users() -> None:
    users_total = await u_domain.count_total_users()

    logger.business_slice("users_total", user_id=None, total=users_total)


async def system_slice_collections() -> None:
    logger.business_slice("collections_total", user_id=None, total=collections.count_total_feeds())


async def system_slice_processors() -> None:
    pointers_list = await ln_domain.get_all_pointers()
    pointers = {pointer.processor_id: pointer for pointer in pointers_list}

    processed_processors = set()

    for processor in background_processors.processors:
        processed_processors.add(processor.id)

        pointer = pointers.get(processor.id)

        if pointer is None:
            logger.business_slice(
                "processor_pointer",
                user_id=None,
                processor_id=processor.id,
                is_active=True,
                pointer_created_at=int(utils.zero_timestamp().timestamp()),
            )
            continue

        logger.business_slice(
            "processor_pointer",
            user_id=None,
            processor_id=processor.id,
            is_active=True,
            pointer_created_at=int(pointer.pointer_created_at.timestamp()),
        )

    for pointer in pointers_list:
        if pointer.processor_id in processed_processors:
            continue

        logger.business_slice(
            "processor_pointer",
            user_id=None,
            processor_id=pointer.processor_id,
            is_active=False,
            pointer_created_at=int(pointer.pointer_created_at.timestamp()),
        )


async def run_system() -> None:

    async with with_app():
        await system_slice_tags()
        await system_slice_new_tags_count()
        await system_slice_tag_frequencies()
        await system_slice_feeds()
        await system_slice_entries()
        await system_slice_users()
        await system_slice_collections()
        await system_slice_processors()


@cli_app.command()
def system() -> None:
    asyncio.run(run_system())


##############
# User metrics
##############


async def users_slice_rules() -> None:
    rules_per_user = await s_domain.count_rules_per_user()

    for user_id, count in rules_per_user.items():
        if count == 0:
            continue
        logger.business_slice("rules_per_user", user_id=user_id, total=count)


async def count_collections_for_users() -> None:  # noqa: CCR001
    collection_users: dict[UserId, dict[CollectionId, int]] = {}

    for collection in collections.collections():
        feed_ids: list[FeedId] = [feed_info.feed_id for feed_info in collection.feeds]  # type: ignore

        counts_for_collection = await fl_domain.count_subset_feeds_per_user(feed_ids)

        for user_id, count in counts_for_collection.items():
            if user_id not in collection_users:
                collection_users[user_id] = {}

            collection_users[user_id][collection.id] = count

    for user_id, counts in collection_users.items():
        if all(count == 0 for count in counts.values()):
            continue

        attributes = {f"collection_{collection_id}": count for collection_id, count in counts.items()}
        logger.business_slice("collection_feeds_per_user", user_id=user_id, **attributes)


async def count_feeds_fun_news_for_users() -> None:  # noqa: CCR001
    feeds_fun_collection_id = CollectionId(uuid.UUID("09887b50-48b0-420a-b614-772e85617cb7"))

    feeds_fun_users: dict[UserId, dict[FeedId, int]] = {}

    for feed_info in collections.collection(feeds_fun_collection_id).feeds:
        assert feed_info.feed_id

        counts_for_feeds_fun = await fl_domain.count_subset_feeds_per_user([feed_info.feed_id])

        for user_id, count in counts_for_feeds_fun.items():
            if user_id not in feeds_fun_users:
                feeds_fun_users[user_id] = {}

            feeds_fun_users[user_id][feed_info.feed_id] = count

    for user_id, counts in feeds_fun_users.items():
        if all(count == 0 for count in counts.values()):
            continue

        attributes = {f"feed_{feed_id}": count for feed_id, count in counts.items()}
        logger.business_slice("feeds_fun_feeds_per_user", user_id=user_id, **attributes)


async def users_slice_feeds_links() -> None:  # noqa: CCR001
    # total feeds per user
    feeds_per_user = await fl_domain.count_feeds_per_user()

    for user_id, count in feeds_per_user.items():
        if count == 0:
            continue

        logger.business_slice("feeds_per_user", user_id=user_id, total=count)

    await count_collections_for_users()

    await count_feeds_fun_news_for_users()


async def users_slice_resources() -> None:  # noqa: CCR001
    from ffun.application.resources import Resource

    users: dict[UserId, dict[str, int]] = {}

    resource_by_kind = {}

    for kind in Resource:
        resource_by_kind[kind] = await r_domain.count_total_resources_per_user(kind)

    for kind, resource_per_user in resource_by_kind.items():
        for user_id, count in resource_per_user.items():
            if user_id not in users:
                users[user_id] = {}

            users[user_id][kind.name] = count

    for user_id, resources in users.items():
        if all(count == 0 for count in resources.values()):
            continue
        logger.business_slice("resources_per_user", user_id=user_id, **resources)


async def run_users() -> None:
    async with with_app():
        await users_slice_rules()
        await users_slice_feeds_links()
        await users_slice_resources()


@cli_app.command()
def users() -> None:
    asyncio.run(run_users())
