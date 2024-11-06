from typing import Iterable

from ffun.core import logging
from ffun.domain.domain import new_feed_id
from ffun.domain.entities import EntryId, FeedId, UserId
from ffun.domain.urls import url_to_source_uid
from ffun.feeds import domain as f_domain
from ffun.feeds import entities as f_entities
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.markers import domain as m_domain
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
