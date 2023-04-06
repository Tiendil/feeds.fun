
import fastapi
from ffun.feeds import domain as f_domain
from ffun.library import domain as l_domain
from ffun.ontology import domain as o_domain
from ffun.scores import domain as s_domain

from . import entities

router = fastapi.APIRouter()


@router.post('/api/get-feeds')
async def api_get_feeds(request: entities.GetFeedsRequest) -> entities.GetFeedsResponse:
    feeds = await f_domain.get_all_feeds()

    return entities.GetFeedsResponse(feeds=[entities.Feed.from_internal(feed) for feed in feeds])


@router.post('/api/get-entries')
async def api_get_entries(request: entities.GetEntriesRequest) -> entities.GetEntriesResponse:
    feeds = await f_domain.get_all_feeds()

    # TODO: limit
    entries = await l_domain.get_entries_by_filter(feeds_ids=[feed.id for feed in feeds],
                                                   limit=10000)

    entries_ids = [entry.id for entry in entries]

    tags = await o_domain.get_tags_for_entries(entries_ids)

    tags_ids = await o_domain.get_tags_ids_for_entries(entries_ids)

    rules = await s_domain.get_rules()

    scores = s_domain.get_scores(rules, tags_ids)

    entries = [entities.Entry.from_internal(entry=entry,
                                            tags=tags.get(entry.id, ()),
                                            score=scores.get(entry.id, 0))
               for entry in entries]

    entries.sort(key=lambda entry: entry.score, reverse=True)

    return entities.GetEntriesResponse(entries=entries)
