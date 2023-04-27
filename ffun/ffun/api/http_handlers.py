
import uuid
from typing import Iterable

import fastapi
from ffun.feeds import domain as f_domain
from ffun.feeds import entities as f_entities
from ffun.feeds_discoverer import domain as fd_domain
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library import entities as l_entities
from ffun.markers import domain as m_domain
from ffun.ontology import domain as o_domain
from ffun.parsers import domain as p_domain
from ffun.scores import domain as s_domain
from ffun.scores import entities as s_entities

from . import entities
from .dependencies import User

router = fastapi.APIRouter()


@router.post('/api/get-feeds')
async def api_get_feeds(request: entities.GetFeedsRequest, user: User) -> entities.GetFeedsResponse:

    linked_feeds_ids = await fl_domain.get_linked_feeds(user.id)

    feeds = await f_domain.get_feeds(linked_feeds_ids)

    return entities.GetFeedsResponse(feeds=[entities.Feed.from_internal(feed) for feed in feeds])


async def _external_entries(entries: Iterable[l_entities.Entry],
                            with_body: bool,
                            user_id: uuid.UUID) -> list[entities.Entry]:
    entries_ids = [entry.id for entry in entries]

    tags = await o_domain.get_tags_for_entries(entries_ids)

    tags_ids = await o_domain.get_tags_ids_for_entries(entries_ids)

    markers = await m_domain.get_markers(user_id=user_id, entries_ids=entries_ids)

    rules = await s_domain.get_rules(user_id)

    external_entries = []

    for entry in entries:
        score = s_domain.get_score(rules, tags_ids.get(entry.id, set()))

        external_markers = [entities.Marker.from_internal(marker) for marker in markers.get(entry.id, ())]

        entry = entities.Entry.from_internal(entry=entry,
                                             tags=tags.get(entry.id, ()),
                                             markers=external_markers,
                                             score=score,
                                             with_body=with_body)

        external_entries.append(entry)

    external_entries.sort(key=lambda entry: entry.score, reverse=True)

    return external_entries


@router.post('/api/get-last-entries')
async def api_get_last_entries(request: entities.GetLastEntriesRequest, user: User) -> entities.GetLastEntriesResponse:

    linked_feeds_ids = await fl_domain.get_linked_feeds(user.id)

    # TODO: limit
    entries = await l_domain.get_entries_by_filter(feeds_ids=linked_feeds_ids,
                                                   period=request.period,
                                                   limit=10000)

    external_entries = await _external_entries(entries, with_body=False, user_id=user.id)

    return entities.GetLastEntriesResponse(entries=external_entries)


@router.post('/api/get-entries-by-ids')
async def api_get_entries_by_ids(request: entities.GetEntriesByIdsRequest, user: User) -> entities.GetEntriesByIdsResponse:
    # TODO: check if belongs to user

    if len(request.ids) > 10:
        # TODO: better error processing
        raise fastapi.HTTPException(status_code=400, detail='Too many ids')

    entries = await l_domain.get_entries_by_ids(request.ids)

    found_entries = [entry for entry in entries.values() if entry is not None]

    external_entries = await _external_entries(found_entries, with_body=True, user_id=user.id)

    return entities.GetEntriesByIdsResponse(entries=external_entries)


@router.post('/api/create-rule')
async def api_create_rule(request: entities.CreateRuleRequest, user: User) -> entities.CreateRuleResponse:
    tags_ids = await o_domain.get_ids_by_tags(request.tags)

    await s_domain.create_rule(user_id=user.id,
                               tags=set(tags_ids.values()),
                               score=request.score)

    return entities.CreateRuleResponse()


@router.post('/api/delete-rule')
async def api_delete_rule(request: entities.DeleteRuleRequest, user: User) -> entities.DeleteRuleResponse:
    await s_domain.delete_rule(user_id=user.id, rule_id=request.id)

    return entities.DeleteRuleResponse()


@router.post('/api/update-rule')
async def api_update_rule(request: entities.UpdateRuleRequest, user: User) -> entities.UpdateRuleResponse:

    tags_ids = await o_domain.get_ids_by_tags(request.tags)

    await s_domain.update_rule(user_id=user.id, rule_id=request.id, score=request.score, tags=tags_ids.values())

    return entities.UpdateRuleResponse()


async def _prepare_rules(rules: Iterable[s_entities.Rule]) -> list[entities.Rule]:
    all_tags = set()

    for rule in rules:
        all_tags.update(rule.tags)

    tags_mapping = await o_domain.get_tags_by_ids(all_tags)

    external_rules = [entities.Rule.from_internal(rule=rule, tags_mapping=tags_mapping) for rule in rules]

    return external_rules


@router.post('/api/get-rules')
async def api_get_rules(request: entities.GetRulesRequest, user: User) -> entities.GetRulesResponse:
    rules = await s_domain.get_rules(user_id=user.id)

    external_rules = await _prepare_rules(rules)

    return entities.GetRulesResponse(rules=external_rules)


@router.post('/api/get-score-details')
async def api_get_score_details(request: entities.GetScoreDetailsRequest, user: User) -> entities.GetScoreDetailsResponse:

    entry_id = request.entryId

    rules = await s_domain.get_rules(user.id)

    tags_ids = await o_domain.get_tags_ids_for_entries([entry_id])

    rules = s_domain.get_score_rules(rules, tags_ids.get(entry_id, set()))

    external_rules = await _prepare_rules(rules)

    return entities.GetScoreDetailsResponse(rules=external_rules)


@router.post('/api/set-marker')
async def api_set_marker(request: entities.SetMarkerRequest, user: User) -> entities.SetMarkerResponse:
    await m_domain.set_marker(user_id=user.id, entry_id=request.entryId, marker=request.marker.to_internal())

    return entities.SetMarkerResponse()


@router.post('/api/remove-marker')
async def api_remove_marker(request: entities.RemoveMarkerRequest, user: User) -> entities.RemoveMarkerResponse:
    await m_domain.remove_marker(user_id=user.id, entry_id=request.entryId, marker=request.marker.to_internal())

    return entities.RemoveMarkerResponse()


@router.post('/api/discover-feeds')
async def api_discover_feeds(request: entities.DiscoverFeedsRequest, user: User) -> entities.DiscoverFeedsResponse:
    feeds = await fd_domain.discover(url=request.url)

    for feed in feeds:
        # TODO: should we limit entities number there?
        feed.entries = feed.entries[:3]

    external_feeds = [entities.FeedInfo.from_internal(feed) for feed in feeds]

    return entities.DiscoverFeedsResponse(feeds=external_feeds)


async def _add_feeds(feed_infos: list[entities.FeedInfo], user: User) -> None:

    feeds = [f_entities.Feed(id=uuid.uuid4(),
                             url=feed_info.url,
                             title=feed_info.title,
                             description=feed_info.description)
             for feed_info in feed_infos]

    real_feeds_ids = await f_domain.save_feeds(feeds)

    for feed_id in real_feeds_ids:
        await fl_domain.add_link(user_id=user.id, feed_id=feed_id)


@router.post('/api/add-feed')
async def api_add_feed(request: entities.AddFeedRequest, user: User) -> entities.AddFeedResponse:
    feed_info = await fd_domain.check_if_feed(url=request.url)

    if feed_info is None:
        raise fastapi.HTTPException(status_code=400, detail='Not a feed')

    await _add_feeds([feed_info], user)

    return entities.AddFeedResponse()


@router.post('/api/add-opml')
async def api_add_opml(request: entities.AddOpmlRequest,
                       user: User) -> entities.AddOpmlResponse:

    feed_infos = p_domain.parse_opml(request.content)

    await _add_feeds(feed_infos, user)

    return entities.AddOpmlResponse()
