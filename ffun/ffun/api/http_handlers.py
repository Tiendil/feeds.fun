
from typing import Iterable

import fastapi
from ffun.feeds import domain as f_domain
from ffun.library import domain as l_domain
from ffun.library import entities as l_entities
from ffun.ontology import domain as o_domain
from ffun.scores import domain as s_domain

from . import entities

router = fastapi.APIRouter()


@router.post('/api/get-feeds')
async def api_get_feeds(request: entities.GetFeedsRequest) -> entities.GetFeedsResponse:
    feeds = await f_domain.get_all_feeds()

    return entities.GetFeedsResponse(feeds=[entities.Feed.from_internal(feed) for feed in feeds])


async def _external_entries(entries: Iterable[l_entities.Entry], with_body: bool) -> list[entities.Entry]:
    entries_ids = [entry.id for entry in entries]

    tags = await o_domain.get_tags_for_entries(entries_ids)

    tags_ids = await o_domain.get_tags_ids_for_entries(entries_ids)

    rules = await s_domain.get_rules()

    scores = s_domain.get_scores(rules, tags_ids)

    entries = [entities.Entry.from_internal(entry=entry,
                                            tags=tags.get(entry.id, ()),
                                            score=scores.get(entry.id, 0),
                                            with_body=with_body)
               for entry in entries]

    entries.sort(key=lambda entry: entry.score, reverse=True)

    return entries


@router.post('/api/get-last-entries')
async def api_get_last_entries(request: entities.GetLastEntriesRequest) -> entities.GetLastEntriesResponse:
    feeds = await f_domain.get_all_feeds()

    # TODO: limit
    entries = await l_domain.get_entries_by_filter(feeds_ids=[feed.id for feed in feeds],
                                                   period=request.period,
                                                   limit=10000)

    external_entries = await _external_entries(entries, with_body=False)

    return entities.GetLastEntriesResponse(entries=external_entries)


@router.post('/api/get-entries-by-ids')
async def api_get_entries_by_ids(request: entities.GetEntriesByIdsRequest) -> entities.GetEntriesByIdsResponse:
    # TODO: check if belongs to user

    if len(request.ids) > 10:
        # TODO: better error processing
        raise fastapi.HTTPException(status_code=400, detail='Too many ids')

    entries = await l_domain.get_entries_by_ids(request.ids)

    found_entries = [entry for entry in entries.values() if entry is not None]

    external_entries = await _external_entries(found_entries, with_body=True)

    return entities.GetEntriesByIdsResponse(entries=external_entries)
