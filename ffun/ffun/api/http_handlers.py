from importlib import metadata
from typing import Any, Iterable

import fastapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse

from ffun.api import entities
from ffun.api.settings import settings
from ffun.auth.dependencies import User
from ffun.core import logging
from ffun.core.api import Message, MessageType
from ffun.core.errors import APIError
from ffun.domain.entities import UserId
from ffun.domain.urls import url_to_uid
from ffun.feeds import domain as f_domain
from ffun.feeds_collections.collections import collections
from ffun.feeds_discoverer import domain as fd_domain
from ffun.feeds_discoverer import entities as fd_entities
from ffun.feeds_links import domain as fl_domain
from ffun.library import domain as l_domain
from ffun.library import entities as l_entities
from ffun.markers import domain as m_domain
from ffun.meta import domain as meta_domain
from ffun.ontology import domain as o_domain
from ffun.parsers import domain as p_domain
from ffun.parsers import entities as p_entities
from ffun.resources import domain as r_domain
from ffun.scores import domain as s_domain
from ffun.scores import entities as s_entities
from ffun.user_settings import domain as us_domain

router = fastapi.APIRouter()

logger = logging.get_module_logger()


@router.post("/api/test/internal-error")
async def api_internal_error() -> None:
    raise Exception("test_error")


@router.post("/api/test/expected-error")
async def api_expected_error() -> None:
    raise APIError(code="expected_test_error", message="Expected test error")


@router.post("/api/test/ok")
async def api_ok() -> None:
    return None


@router.post("/api/get-feeds")
async def api_get_feeds(request: entities.GetFeedsRequest, user: User) -> entities.GetFeedsResponse:
    linked_feeds = await fl_domain.get_linked_feeds(user.id)

    feeds_to_links = {link.feed_id: link for link in linked_feeds}

    feeds = await f_domain.get_feeds(ids=list(feeds_to_links.keys()))

    external_feeds = []

    for feed in feeds:
        collection_ids = collections.collections_for_feed(feed.id)
        external_feed = entities.Feed.from_internal(feed, link=feeds_to_links[feed.id], collection_ids=collection_ids)
        external_feeds.append(external_feed)

    return entities.GetFeedsResponse(feeds=external_feeds)


async def _external_entries(  # pylint: disable=R0914
    entries: Iterable[l_entities.Entry], with_body: bool, user_id: UserId
) -> tuple[list[entities.Entry], dict[int, str]]:
    entries_ids = [entry.id for entry in entries]

    tags_ids = await o_domain.get_tags_ids_for_entries(entries_ids)

    if tags_ids:
        whole_tags = set.union(*tags_ids.values())
    else:
        whole_tags = set()

    tags_mapping = await o_domain.get_tags_by_ids(whole_tags)

    markers = await m_domain.get_markers(user_id=user_id, entries_ids=entries_ids)

    rules = await s_domain.get_rules(user_id)

    external_entries = []

    for entry in entries:
        score, contributions_by_ids = s_domain.get_score_contributions(rules, tags_ids.get(entry.id, set()))

        external_markers = [entities.Marker.from_internal(marker) for marker in markers.get(entry.id, ())]

        external_entry = entities.Entry.from_internal(
            entry=entry,
            tags=tags_ids.get(entry.id, ()),
            markers=external_markers,
            score=score,
            score_contributions=contributions_by_ids,
            with_body=with_body,
        )

        external_entries.append(external_entry)

    external_entries.sort(key=lambda entry: entry.score, reverse=True)

    return external_entries, tags_mapping


@router.post("/api/get-last-entries")
async def api_get_last_entries(request: entities.GetLastEntriesRequest, user: User) -> entities.GetLastEntriesResponse:
    linked_feeds = await fl_domain.get_linked_feeds(user.id)

    linked_feeds_ids = [link.feed_id for link in linked_feeds]

    entries = await l_domain.get_entries_by_filter(
        feeds_ids=linked_feeds_ids, period=request.period, limit=settings.max_returned_entries
    )

    external_entries, tags_mapping = await _external_entries(entries, with_body=False, user_id=user.id)

    return entities.GetLastEntriesResponse(entries=external_entries, tagsMapping=tags_mapping)


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

    external_entries, tags_mapping = await _external_entries(found_entries, with_body=True, user_id=user.id)

    return entities.GetEntriesByIdsResponse(entries=external_entries, tagsMapping=tags_mapping)


@router.post("/api/create-or-update-rule")
async def api_create_or_update_rule(
    request: entities.CreateOrUpdateRuleRequest, user: User
) -> entities.CreateOrUpdateRuleResponse:
    required_tags_ids = await o_domain.get_ids_by_uids(request.requiredTags)
    excluded_tags_ids = await o_domain.get_ids_by_uids(request.excludedTags)

    await s_domain.create_or_update_rule(
        user_id=user.id,
        score=request.score,
        required_tags=required_tags_ids.values(),
        excluded_tags=excluded_tags_ids.values(),
    )

    return entities.CreateOrUpdateRuleResponse()


@router.post("/api/delete-rule")
async def api_delete_rule(request: entities.DeleteRuleRequest, user: User) -> entities.DeleteRuleResponse:
    await s_domain.delete_rule(user_id=user.id, rule_id=request.id)

    return entities.DeleteRuleResponse()


@router.post("/api/update-rule")
async def api_update_rule(request: entities.UpdateRuleRequest, user: User) -> entities.UpdateRuleResponse:
    required_tags_ids = await o_domain.get_ids_by_uids(request.requiredTags)
    excluded_tags_ids = await o_domain.get_ids_by_uids(request.excludedTags)

    await s_domain.update_rule(
        user_id=user.id,
        rule_id=request.id,
        score=request.score,
        required_tags=required_tags_ids.values(),
        excluded_tags=excluded_tags_ids.values(),
    )

    return entities.UpdateRuleResponse()


async def _prepare_rules(rules: Iterable[s_entities.Rule]) -> list[entities.Rule]:
    all_tags = set()

    for rule in rules:
        all_tags.update(rule.required_tags)
        all_tags.update(rule.excluded_tags)

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
    result = await fd_domain.discover(url=request.url, depth=1)

    messages = []

    # descriptive user friendly error messages
    results_to_messages = {
        fd_entities.Status.incorrect_url: "The URL has incorrect format",
        fd_entities.Status.cannot_access_url: "Cannot access the URL",
        fd_entities.Status.not_html: "Can not parse content of the page",
        fd_entities.Status.no_feeds_found: "No feeds found at the specified URL",
    }

    if result.status == fd_entities.Status.feeds_found:
        pass
    elif result.status in results_to_messages:
        messages.append(
            Message(
                type=MessageType.error,
                code=f"discover_feeds_error:{result.status.name}",
                message=results_to_messages[result.status],
            )
        )
    else:
        raise NotImplementedError(f"Unknown status: {result.status}")

    linked_feeds = await fl_domain.get_linked_feeds(user.id)
    linked_ids = {link.feed_id for link in linked_feeds}

    found_ids = await f_domain.get_feed_ids_by_uids([feed.uid for feed in result.feeds])

    for feed in result.feeds[: settings.max_feeds_suggestions_for_site]:
        feed.entries = feed.entries[: settings.max_entries_suggestions_for_site]

    external_feeds = [
        entities.FeedInfo.from_internal(feed, is_linked=feed.uid in found_ids and found_ids[feed.uid] in linked_ids)
        for feed in result.feeds
    ]

    return entities.DiscoverFeedsResponse(feeds=external_feeds, messages=messages)


@router.post("/api/add-feed")
async def api_add_feed(request: entities.AddFeedRequest, user: User) -> entities.AddFeedResponse:
    discover_result = await fd_domain.discover(url=request.url, depth=0)

    if discover_result.status != fd_entities.Status.feeds_found:
        raise fastapi.HTTPException(status_code=400, detail="Not a feed")

    feed_info = discover_result.feeds[0]

    ids = await meta_domain.add_feeds([feed_info], user.id)

    feed = await f_domain.get_feed(ids[0])

    collection_ids = collections.collections_for_feed(feed.id)

    link = await fl_domain.get_link(user.id, feed.id)

    assert link is not None

    return entities.AddFeedResponse(feed=entities.Feed.from_internal(feed, link=link, collection_ids=collection_ids))


@router.post("/api/add-opml")
async def api_add_opml(request: entities.AddOpmlRequest, user: User) -> entities.AddOpmlResponse:
    feed_infos = p_domain.parse_opml(request.content)

    await meta_domain.add_feeds(feed_infos, user.id)

    logger.business_event("opml_import", user_id=user.id, feeds_count=len(feed_infos))

    return entities.AddOpmlResponse()


@router.get("/api/get-opml")
async def api_get_opml(user: User) -> PlainTextResponse:
    linked_feeds = await fl_domain.get_linked_feeds(user.id)

    linked_feeds_ids = [link.feed_id for link in linked_feeds]

    feeds = await f_domain.get_feeds(ids=linked_feeds_ids)

    content = p_domain.create_opml(feeds=feeds)

    headers = {"Content-Disposition": "attachment; filename=feeds-fun.opml"}

    return PlainTextResponse(content=content, media_type="application/xml", headers=headers)


@router.post("/api/unsubscribe")
async def api_unsubscribe(request: entities.UnsubscribeRequest, user: User) -> entities.UnsubscribeResponse:
    await fl_domain.remove_link(user_id=user.id, feed_id=request.feedId)

    return entities.UnsubscribeResponse()


@router.post("/api/get-collections")
async def api_get_feeds_collections(
    request: entities.GetFeedsCollectionsRequest, user: User
) -> entities.GetFeedsCollectionsResponse:

    internal_collections = collections.collections()

    collections_to_return = [entities.Collection.from_internal(collection) for collection in internal_collections]

    return entities.GetFeedsCollectionsResponse(collections=collections_to_return)


@router.post("/api/get-collection-feeds")
async def api_get_collection_feeds(
    request: entities.GetCollectionFeedsRequest, user: User
) -> entities.GetCollectionFeedsResponse:

    collection = collections.collection(request.collectionId)

    feeds = [entities.CollectionFeedInfo.from_internal(feed_info) for feed_info in collection.feeds]

    return entities.GetCollectionFeedsResponse(feeds=feeds)


@router.post("/api/subscribe-to-collections")
async def api_subscribe_to_collections(
    request: entities.SubscribeToCollectionsRequest, user: User
) -> entities.SubscribeToCollectionsResponse:
    feeds = []

    for collection_id in request.collections:
        collection = collections.collection(collection_id)

        for feed_info in collection.feeds:
            feeds.append(
                p_entities.FeedInfo(
                    url=feed_info.url,
                    title=feed_info.title,
                    description=feed_info.description,
                    entries=[],
                    uid=url_to_uid(feed_info.url),
                )
            )

    await meta_domain.add_feeds(feeds, user.id)

    return entities.SubscribeToCollectionsResponse()


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
        if kind == UserSetting.test_api_key:
            continue

        result_values.append(entities.UserSetting.from_internal(kind, value))

    return entities.GetUserSettingsResponse(settings=result_values)


@router.post("/api/set-user-setting")
async def api_set_user_setting(request: entities.SetUserSettingRequest, user: User) -> entities.SetUserSettingResponse:
    await us_domain.save_setting(user_id=user.id, kind=request.kind.to_internal(), value=request.value)

    return entities.SetUserSettingResponse()


@router.post("/api/track-event")
async def api_track_event(request: entities.TrackEventRequest, user: User) -> entities.TrackEventResponse:
    attributes = request.event.model_dump()
    event = attributes.pop("name")

    logger.business_event(event, user_id=user.id, **attributes)

    return entities.TrackEventResponse()


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
