
import uuid
from typing import Iterable

import fastapi
from ffun.feeds import domain as f_domain
from ffun.library import domain as l_domain
from ffun.library import entities as l_entities
from ffun.ontology import domain as o_domain
from ffun.scores import domain as s_domain
from ffun.scores import entities as s_entities

from . import entities
from .dependencies import User

router = fastapi.APIRouter()


@router.post('/api/get-feeds')
async def api_get_feeds(request: entities.GetFeedsRequest) -> entities.GetFeedsResponse:
    feeds = await f_domain.get_all_feeds()

    return entities.GetFeedsResponse(feeds=[entities.Feed.from_internal(feed) for feed in feeds])


async def _external_entries(entries: Iterable[l_entities.Entry],
                            with_body: bool,
                            user_id: uuid.UUID) -> list[entities.Entry]:
    entries_ids = [entry.id for entry in entries]

    tags = await o_domain.get_tags_for_entries(entries_ids)

    tags_ids = await o_domain.get_tags_ids_for_entries(entries_ids)

    rules = await s_domain.get_rules(user_id)

    external_entries = []

    for entry in entries:
        score = s_domain.get_score(rules, tags_ids.get(entry.id, set()))

        entry = entities.Entry.from_internal(entry=entry,
                                             tags=tags.get(entry.id, ()),
                                             score=score,
                                             with_body=with_body)

        external_entries.append(entry)

    external_entries.sort(key=lambda entry: entry.score, reverse=True)

    return external_entries


@router.post('/api/get-last-entries')
async def api_get_last_entries(request: entities.GetLastEntriesRequest, user: User) -> entities.GetLastEntriesResponse:
    feeds = await f_domain.get_all_feeds()

    # TODO: limit
    entries = await l_domain.get_entries_by_filter(feeds_ids=[feed.id for feed in feeds],
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
