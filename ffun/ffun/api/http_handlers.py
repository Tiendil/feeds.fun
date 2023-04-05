
import fastapi
from ffun.feeds import domain as f_domain
from ffun.library import domain as l_domain
from ffun.ontology import domain as o_domain

from . import entities

router = fastapi.APIRouter()


@router.post('/api/get-feeds')
async def api_get_feeds(request: entities.GetFeedsRequest) -> entities.GetFeedsResponse:
    feeds = await f_domain.get_all_feeds()

    return entities.GetFeedsResponse(feeds=[entities.Feed.from_internal(feed) for feed in feeds])


@router.post('/api/get-entries')
async def api_get_entries(request: entities.GetEntriesRequest) -> entities.GetEntriesResponse:
    feeds = await f_domain.get_all_feeds()

    entries = await l_domain.get_entries_by_filter(feeds_ids=[feed.id for feed in feeds],
                                                   limit=10000)

    tags = await o_domain.get_tags_for_entries([entry.id for entry in entries])

    return entities.GetEntriesResponse(entries=[entities.Entry.from_internal(entry=entry,
                                                                             tags=tags.get(entry.id, ()))
                                                for entry in entries])
