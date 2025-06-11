from typing import Iterable

from ffun.core import logging, utils
from ffun.domain.domain import new_feed_id
from ffun.domain.entities import EntryId, FeedId, UserId
from ffun.domain.urls import url_to_source_uid
from ffun.feeds import domain as f_domain
from ffun.feeds import entities as f_entities
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.markers import domain as m_domain
from ffun.meta.settings import settings
from ffun.ontology import domain as o_domain
from ffun.parsers import entities as p_entities

logger = logging.get_module_logger()


# Note: fully unlinked entry can be linked again before removing from l_entries
#       we should do something with it in the future, but it is ok for now
#       there should not a lot of such cases
async def remove_entries(entries_ids: Iterable[EntryId]) -> None:
    """Remove entries and all related markers and relations."""
    entries_to_remove = list(entries_ids)

    await m_domain.remove_markers_for_entries(entries_to_remove)
    await o_domain.remove_relations_for_entries(entries_to_remove)
    await l_domain.remove_entries_by_ids(entries_to_remove)


async def add_feeds(feed_infos: list[p_entities.FeedInfo], user_id: UserId) -> list[FeedId]:

    urls_to_sources_uids = {feed_info.url: url_to_source_uid(feed_info.url) for feed_info in feed_infos}

    sources_uids_to_ids = await f_domain.get_source_ids(urls_to_sources_uids.values())

    feeds = [
        f_entities.Feed(
            id=new_feed_id(),
            source_id=sources_uids_to_ids[urls_to_sources_uids[feed_info.url]],
            url=feed_info.url,
            title=feed_info.title,
            description=feed_info.description,
        )
        for feed_info in feed_infos
    ]

    real_feeds_ids = await f_domain.save_feeds(feeds)

    for feed_id in real_feeds_ids:
        await fl_domain.add_link(user_id=user_id, feed_id=feed_id)

    return real_feeds_ids


async def clean_orphaned_entries(chunk: int) -> int:
    orphanes = await l_domain.get_orphaned_entries(limit=chunk)

    await remove_entries(orphanes)

    return len(orphanes)


# There is a very small possibility, that user will link feed
# while we in the process of removing it as an orphaned feed.
# This is look like an almost impossible situation (on the current load), because:
# - the feed must be marked as orphaned before that
# - we wait a timeout before removing orphaned feeds
# - the user should make their operations right at the time we process orphaned feeds
async def clean_orphaned_feeds(chunk: int) -> int:
    loaded_before = utils.now() - settings.delay_before_removing_orphaned_feeds

    orphanes = await f_domain.get_orphaned_feeds(limit=chunk, loaded_before=loaded_before)

    # ensure deterministic order of processing
    orphanes.sort()

    # refactor this loop into a bulk operation calls in case of performance issues
    for orphan_id in orphanes:
        logger.info("removing_orphaned_feed", feed_id=orphan_id)

        # unlink all linked entries
        await l_domain.unlink_feed_tail(orphan_id, offset=0)

        await f_domain.tech_remove_feed(orphan_id)

    # just a protection in case some user linked feed while we were removing it
    # in that case return DB in the consistent state
    await fl_domain.tech_remove_all_links(orphanes)

    return len(orphanes)
