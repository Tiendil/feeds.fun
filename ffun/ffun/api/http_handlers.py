import uuid
from importlib import metadata
from typing import Any, Iterable

import fastapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse

from ffun.api import entities
from ffun.api.settings import settings
from ffun.auth.dependencies import User
from ffun.core import logging
from ffun.feeds import domain as f_domain
from ffun.feeds import entities as f_entities
from ffun.feeds_collections import domain as fc_domain
from ffun.feeds_discoverer import domain as fd_domain
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library import entities as l_entities
from ffun.markers import domain as m_domain
from ffun.ontology import domain as o_domain
from ffun.parsers import domain as p_domain
from ffun.parsers import entities as p_entities
from ffun.resources import domain as r_domain
from ffun.scores import domain as s_domain
from ffun.scores import entities as s_entities
from ffun.user_settings import domain as us_domain

router = fastapi.APIRouter()

logger = logging.get_module_logger()


@router.post("/api/error")
async def api_error() -> None:
    raise Exception("test_error")


@router.post("/api/get-feeds")
async def api_get_feeds(request: entities.GetFeedsRequest, user: User) -> entities.GetFeedsResponse:
    linked_feeds = await fl_domain.get_linked_feeds(user.id)

    feeds_to_links = {link.feed_id: link for link in linked_feeds}

    feeds = await f_domain.get_feeds(ids=list(feeds_to_links.keys()))

    return entities.GetFeedsResponse(
        feeds=[entities.Feed.from_internal(feed, link=feeds_to_links[feed.id]) for feed in feeds]
    )


async def _external_entries(  # pylint: disable=R0914
    entries: Iterable[l_entities.Entry], with_body: bool, user_id: uuid.UUID
) -> list[entities.Entry]:
    entries_ids = [entry.id for entry in entries]

    tags = await o_domain.get_tags_for_entries(entries_ids)

    tags_ids = await o_domain.get_tags_ids_for_entries(entries_ids)

    markers = await m_domain.get_markers(user_id=user_id, entries_ids=entries_ids)

    rules = await s_domain.get_rules(user_id)

    external_entries = []

    for entry in entries:
        score, contributions_by_ids = s_domain.get_score_contributions(rules, tags_ids.get(entry.id, set()))

        tags_mapping = await o_domain.get_tags_by_ids(contributions_by_ids.keys())

        contributions_by_str = {
            tags_mapping[tag_id]: contribution for tag_id, contribution in contributions_by_ids.items()
        }

        external_markers = [entities.Marker.from_internal(marker) for marker in markers.get(entry.id, ())]

        external_entry = entities.Entry.from_internal(
            entry=entry,
            tags=tags.get(entry.id, ()),
            markers=external_markers,
            score=score,
            score_contributions=contributions_by_str,
            with_body=with_body,
        )

        external_entries.append(external_entry)

    external_entries.sort(key=lambda entry: entry.score, reverse=True)

    return external_entries


@router.post("/api/get-last-entries")
async def api_get_last_entries(request: entities.GetLastEntriesRequest, user: User) -> entities.GetLastEntriesResponse:
    linked_feeds = await fl_domain.get_linked_feeds(user.id)

    linked_feeds_ids = [link.feed_id for link in linked_feeds]

    entries = await l_domain.get_entries_by_filter(
        feeds_ids=linked_feeds_ids, period=request.period, limit=settings.max_returned_entries
    )

    external_entries = await _external_entries(entries, with_body=False, user_id=user.id)

    return entities.GetLastEntriesResponse(entries=external_entries)


@router.post("/api/get-entries-by-ids")
async def api_get_entries_by_ids(
    request: entities.GetEntriesByIdsRequest, user: User
) -> entities.GetEntriesByIdsResponse:
    # TODO: check if belongs to user

    if len(request.ids) > 10:
        # TODO: better error processing
        raise fastapi.HTTPException(status_code=400, detail="Too many ids")

    entries = await l_domain.get_entries_by_ids(request.ids)

    found_entries = [entry for entry in entries.values() if entry is not None]

    external_entries = await _external_entries(found_entries, with_body=True, user_id=user.id)

    return entities.GetEntriesByIdsResponse(entries=external_entries)


@router.post("/api/create-or-update-rule")
async def api_create_or_update_rule(
    request: entities.CreateOrUpdateRuleRequest, user: User
) -> entities.CreateOrUpdateRuleResponse:
    tags_ids = await o_domain.get_ids_by_uids(request.tags)

    await s_domain.create_or_update_rule(user_id=user.id, tags=set(tags_ids.values()), score=request.score)

    return entities.CreateOrUpdateRuleResponse()


@router.post("/api/delete-rule")
async def api_delete_rule(request: entities.DeleteRuleRequest, user: User) -> entities.DeleteRuleResponse:
    await s_domain.delete_rule(user_id=user.id, rule_id=request.id)

    return entities.DeleteRuleResponse()


@router.post("/api/update-rule")
async def api_update_rule(request: entities.UpdateRuleRequest, user: User) -> entities.UpdateRuleResponse:
    tags_ids = await o_domain.get_ids_by_uids(request.tags)

    await s_domain.update_rule(user_id=user.id, rule_id=request.id, score=request.score, tags=tags_ids.values())

    return entities.UpdateRuleResponse()


async def _prepare_rules(rules: Iterable[s_entities.Rule]) -> list[entities.Rule]:
    all_tags = set()

    for rule in rules:
        all_tags.update(rule.tags)

    tags_mapping = await o_domain.get_tags_by_ids(all_tags)

    external_rules = [entities.Rule.from_internal(rule=rule, tags_mapping=tags_mapping) for rule in rules]

    return external_rules


@router.post("/api/get-rules")
async def api_get_rules(request: entities.GetRulesRequest, user: User) -> entities.GetRulesResponse:
    rules = await s_domain.get_rules(user_id=user.id)

    external_rules = await _prepare_rules(rules)

    return entities.GetRulesResponse(rules=external_rules)


@router.post("/api/get-score-details")
async def api_get_score_details(
    request: entities.GetScoreDetailsRequest, user: User
) -> entities.GetScoreDetailsResponse:
    entry_id = request.entryId

    rules = await s_domain.get_rules(user.id)

    tags_ids = await o_domain.get_tags_ids_for_entries([entry_id])

    rules = s_domain.get_score_rules(rules, tags_ids.get(entry_id, set()))

    external_rules = await _prepare_rules(rules)

    return entities.GetScoreDetailsResponse(rules=external_rules)


@router.post("/api/set-marker")
async def api_set_marker(request: entities.SetMarkerRequest, user: User) -> entities.SetMarkerResponse:
    await m_domain.set_marker(user_id=user.id, entry_id=request.entryId, marker=request.marker.to_internal())

    return entities.SetMarkerResponse()


@router.post("/api/remove-marker")
async def api_remove_marker(request: entities.RemoveMarkerRequest, user: User) -> entities.RemoveMarkerResponse:
    await m_domain.remove_marker(user_id=user.id, entry_id=request.entryId, marker=request.marker.to_internal())

    return entities.RemoveMarkerResponse()


@router.post("/api/discover-feeds")
async def api_discover_feeds(request: entities.DiscoverFeedsRequest, user: User) -> entities.DiscoverFeedsResponse:
    feeds = await fd_domain.discover(url=request.url)

    for feed in feeds:
        # TODO: should we limit entities number there?
        feed.entries = feed.entries[:3]

    external_feeds = [entities.FeedInfo.from_internal(feed) for feed in feeds]

    return entities.DiscoverFeedsResponse(feeds=external_feeds)


async def _add_feeds(feed_infos: list[p_entities.FeedInfo], user: User) -> None:
    feeds = [
        f_entities.Feed(id=uuid.uuid4(), url=feed_info.url, title=feed_info.title, description=feed_info.description)
        for feed_info in feed_infos
    ]

    real_feeds_ids = await f_domain.save_feeds(feeds)

    for feed_id in real_feeds_ids:
        await fl_domain.add_link(user_id=user.id, feed_id=feed_id)


@router.post("/api/add-feed")
async def api_add_feed(request: entities.AddFeedRequest, user: User) -> entities.AddFeedResponse:
    feed_info = await fd_domain.check_if_feed(url=request.url)

    if feed_info is None:
        raise fastapi.HTTPException(status_code=400, detail="Not a feed")

    await _add_feeds([feed_info], user)

    return entities.AddFeedResponse()


@router.post("/api/add-opml")
async def api_add_opml(request: entities.AddOpmlRequest, user: User) -> entities.AddOpmlResponse:
    feed_infos = p_domain.parse_opml(request.content)

    await _add_feeds(feed_infos, user)

    return entities.AddOpmlResponse()


@router.post("/api/unsubscribe")
async def api_unsubscribe(request: entities.UnsubscribeRequest, user: User) -> entities.UnsubscribeResponse:
    await fl_domain.remove_link(user_id=user.id, feed_id=request.feedId)

    return entities.UnsubscribeResponse()


@router.post("/api/get-feeds-collections")
async def api_get_feeds_collections(
    request: entities.GetFeedsCollectionsRequest, user: User
) -> entities.GetFeedsCollectionsResponse:
    collections = list(fc_domain.get_collections())

    return entities.GetFeedsCollectionsResponse(collections=collections)


@router.post("/api/subscribe-to-feeds-collections")
async def api_subscribe_to_feeds_collections(
    request: entities.SubscribeToFeedsCollectionsRequest, user: User
) -> entities.SubscribeToFeedsCollectionsResponse:
    feeds = []

    for collection in request.collections:
        feed_urls = fc_domain.get_feeds_for_collecton(collection)

        for feed_url in feed_urls:
            feeds.append(p_entities.FeedInfo(url=feed_url, title="unknown", description="unknown", entries=[]))

    await _add_feeds(feeds, user)

    return entities.SubscribeToFeedsCollectionsResponse()


@router.post("/api/get-tags-info")
async def api_get_tags_info(request: entities.GetTagsInfoRequest, user: User) -> entities.GetTagsInfoResponse:
    tags_ids = await o_domain.get_ids_by_uids(request.uids)

    info = await o_domain.get_tags_info(tags_ids.values())

    tags_info = {}

    for uid in request.uids:
        tags_info[uid] = entities.TagInfo.from_internal(info[tags_ids[uid]], uid)

    return entities.GetTagsInfoResponse(tags=tags_info)


@router.post("/api/get-resource-history")
async def api_get_resource_history(
    request: entities.GetResourceHistoryRequest, user: User
) -> entities.GetResourceHistoryResponse:
    history = await r_domain.load_resource_history(user_id=user.id, kind=request.kind.to_internal())

    return entities.GetResourceHistoryResponse(
        history=[entities.ResourceHistoryRecord.from_internal(resource) for resource in history]
    )


@router.post("/api/get-info")
async def api_get_info(request: entities.GetInfoRequest, user: User) -> entities.GetInfoResponse:
    return entities.GetInfoResponse(userId=user.id)


###############
# user settings
###############


@router.post("/api/get-user-settings")
async def api_get_user_settings(
    request: entities.GetUserSettingsRequest, user: User
) -> entities.GetUserSettingsResponse:
    from ffun.application.user_settings import UserSetting

    values = await us_domain.load_settings(user_id=user.id, kinds=[int(kind) for kind in UserSetting])

    result_values = []

    for kind, value in values.items():
        result_values.append(entities.UserSetting.from_internal(kind, value))

    return entities.GetUserSettingsResponse(settings=result_values)


@router.post("/api/set-user-setting")
async def api_set_user_setting(request: entities.SetUserSettingRequest, user: User) -> entities.SetUserSettingResponse:
    await us_domain.save_setting(user_id=user.id, kind=request.kind.to_internal(), value=request.value)

    return entities.SetUserSettingResponse()


#######################
# Swagger documentation
#######################

swagger_ui_api_parameters: dict[str, Any] = {
    "defaultModelsExpandDepth": -1,
    "defaultModelExpandDepth": 10,
}


swagger_title = "Feeds Fun API"


swagger_description = """
Greetings!

Welcome to the documentation for the Feeds Fun API.

Please note that the project is currently in its early stages of development, and as such, the API may undergo \
significant changes. We appreciate your understanding and patience during this phase.

At present, our **documentation does not include information regarding authentication**. If you wish to utilize API \
from [feeds.fun](https://feeds.fun), we recommend referring to the [supertokens](https://supertokens.com/) \
documentation for guidance on this matter. We'll improve this aspect of the documentation in the future.

For additional resources, please visit the following links:

- [Feeds Fun Website](https://feeds.fun)
- [GitHub Repository](https://github.com/Tiendil/feeds.fun)

Thank you for your interest in the Feeds Fun API. We look forward to your contributions and feedback.

"""


@router.get("/api/openapi.json", include_in_schema=False)
async def openapi(request: fastapi.Request) -> JSONResponse:
    content = get_openapi(
        title="Feeds Fun API",
        version=metadata.version("ffun"),
        description=swagger_description,
        routes=request.app.routes,
    )

    return JSONResponse(content=content)


@router.get("/api/docs", include_in_schema=False)
async def docs(request: fastapi.Request) -> HTMLResponse:
    openapi_url = request.scope.get("root_path", "") + "/api/openapi.json"

    return get_swagger_ui_html(
        openapi_url=openapi_url, title=swagger_title, swagger_ui_parameters=swagger_ui_api_parameters
    )
