from importlib import metadata
from typing import Any, Iterable

import fastapi
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse

from ffun.api.spa import entities
from ffun.api.spa.settings import settings
from ffun.auth import domain as a_domain
from ffun.auth.dependencies import User
from ffun.auth.settings import settings as auth_settings
from ffun.core import logging, utils
from ffun.core.api import Message, MessageType
from ffun.core.errors import APIError
from ffun.data_protection import domain as dp_domain
from ffun.domain.entities import TagId, TagUid, UserId
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

logger = logging.get_module_logger()

router = fastapi.APIRouter()

api_auth = fastapi.APIRouter(prefix="/spa/auth", tags=["auth"])
api_docs = fastapi.APIRouter(prefix="/spa/docs", tags=["docs"])
api_test = fastapi.APIRouter(prefix="/spa/test", tags=["test"])
api_public = fastapi.APIRouter(prefix="/spa/api/public", tags=["public"])
api_private = fastapi.APIRouter(prefix="/spa/api/private", tags=["private"])


def add_routes_to_app(app: fastapi.FastAPI) -> None:
    app.include_router(api_auth)
    app.include_router(api_docs)
    app.include_router(api_test)
    app.include_router(api_public)
    app.include_router(api_private)


async def _external_entries(  # pylint: disable=R0914
    entries: Iterable[l_entities.Entry],
    with_body: bool,
    user_id: UserId | None,
    min_tag_count: int,
) -> tuple[list[entities.Entry], dict[TagId, TagUid]]:

    entries_ids = [entry.id for entry in entries]

    ########################
    # load rules and markers
    ########################

    if user_id is not None:
        markers = await m_domain.get_markers(user_id=user_id, entries_ids=entries_ids)
        rules = await s_domain.get_rules_for_user(user_id)
    else:
        markers = {}
        rules = []

    ##############
    # process tags
    ##############

    must_have_tags = set()
    for rule in rules:
        must_have_tags.update(rule.required_tags)
        must_have_tags.update(rule.excluded_tags)

    entry_tag_ids, tag_mapping = await o_domain.prepare_tags_for_entries(
        entry_ids=entries_ids, must_have_tags=must_have_tags, min_tag_count=min_tag_count
    )

    ####################
    # construct response
    ####################

    external_entries = []

    for entry in entries:
        score, contributions_by_ids = s_domain.get_score_contributions(rules, entry_tag_ids.get(entry.id, set()))

        external_markers = [entities.Marker.from_internal(marker) for marker in markers.get(entry.id, ())]

        external_entry = entities.Entry.from_internal(
            entry=entry,
            tags=entry_tag_ids.get(entry.id, ()),
            markers=external_markers,
            score=score,
            score_contributions=contributions_by_ids,
            with_body=with_body,
        )

        external_entries.append(external_entry)

    external_entries.sort(key=lambda entry: entry.score, reverse=True)

    return external_entries, tag_mapping


# Frontend may send events with text/plain content-type
# To ensure delivery and avoid preflight CORS requests for simple events tracking
# For example, when user is redirected to another domain and the current page is unloaded
# => we expect request body to be raw JSON string and we parse it manually
async def process_api_track(body: str, user_id: UserId | None) -> entities.TrackEventResponse:
    request = entities.TrackEventRequest.model_validate_json(body)

    attributes = request.event.model_dump()
    event = attributes.pop("name")

    logger.business_event(event, user_id=user_id, **attributes)

    return entities.TrackEventResponse()


async def process_api_get_entries(
    request: entities.GetEntriesByIdsRequest, user_id: UserId | None
) -> entities.GetEntriesByIdsResponse:
    if len(request.ids) > settings.max_entries_details_requests:
        # TODO: better error processing
        raise fastapi.HTTPException(status_code=400, detail="Too many ids")

    entries = await l_domain.get_entries_by_ids(request.ids)

    found_entries = [entry for entry in entries.values() if entry is not None]

    # We cannot know here the whole distribution of tags on the user side
    # => we set min_tag_count=0
    external_entries, tags_mapping = await _external_entries(
        found_entries, with_body=True, user_id=user_id, min_tag_count=0
    )

    return entities.GetEntriesByIdsResponse(entries=external_entries, tagsMapping=tags_mapping)


#####################
# OIDC login redirect
#####################


@api_auth.get("/login")
async def api_auth_login(return_to: str, user: User) -> RedirectResponse:
    """Dummy endpoint to trigger OIDC login flow and redirect to return_to URL if logged in."""
    return RedirectResponse(url=return_to)


@api_auth.get("/join")
async def api_auth_join(return_to: str, user: User) -> RedirectResponse:
    """Dummy endpoint to trigger OIDC registration flow and redirect to return_to URL if logged in."""
    return RedirectResponse(url=return_to)


@api_auth.get("/redirect")
async def api_auth_redirect(return_to: str, user: User) -> RedirectResponse:
    """Redirect endpoint for OIDC login flow."""
    return RedirectResponse(url=return_to)


##################
# Public test APIs
##################


@api_test.post("/internal-error")
async def api_internal_error() -> None:
    raise Exception("test_error")


@api_test.post("/expected-error")
async def api_expected_error() -> None:
    raise APIError(code="expected_test_error", message="Expected test error")


@api_test.post("/ok")
async def api_ok() -> None:
    return None


#############
# Public APIs
#############


@api_public.post("/get-last-collection-entries")
async def api_get_last_collection_entries(
    request: entities.GetLastCollectionEntriesRequest,
) -> entities.GetLastCollectionEntriesResponse:

    collection = collections.collection_by_slug(request.collectionSlug)

    feed_ids = [feed_info.feed_id for feed_info in collection.feeds if feed_info.feed_id is not None]

    entries = await l_domain.get_entries_by_filter_with_fallback(
        feeds_ids=feed_ids,
        period=request.period,
        limit=settings.max_returned_entries,
        fallback_limit=settings.news_outside_period,
    )

    external_entries, tags_mapping = await _external_entries(
        entries, with_body=False, user_id=None, min_tag_count=request.minTagCount
    )

    return entities.GetLastCollectionEntriesResponse(entries=external_entries, tagsMapping=tags_mapping)


@api_public.post("/get-entries-by-ids")
async def api_get_entries_by_ids_public(
    request: entities.GetEntriesByIdsRequest,
) -> entities.GetEntriesByIdsResponse:
    return await process_api_get_entries(request, user_id=None)


@api_public.post("/get-collections")
async def api_get_feeds_collections(
    request: entities.GetFeedsCollectionsRequest,
) -> entities.GetFeedsCollectionsResponse:

    internal_collections = collections.collections()

    collections_to_return = [entities.Collection.from_internal(collection) for collection in internal_collections]

    return entities.GetFeedsCollectionsResponse(collections=collections_to_return)


@api_public.post("/get-collection-feeds")
async def api_get_collection_feeds(request: entities.GetCollectionFeedsRequest) -> entities.GetCollectionFeedsResponse:

    collection = collections.collection(request.collectionId)

    feeds = [entities.CollectionFeedInfo.from_internal(feed_info) for feed_info in collection.feeds]

    return entities.GetCollectionFeedsResponse(feeds=feeds)


@api_public.post("/get-tags-info")
async def api_get_tags_info(request: entities.GetTagsInfoRequest) -> entities.GetTagsInfoResponse:
    tags_ids = await o_domain.get_ids_by_uids(request.uids)

    info = await o_domain.get_tags_info(tags_ids.values())

    tags_info = {}

    for uid in request.uids:
        tags_info[uid] = entities.TagInfo.from_internal(info[tags_ids[uid]], uid)

    return entities.GetTagsInfoResponse(tags=tags_info)


@api_public.post("/get-info")
async def api_get_info(request: entities.GetInfoRequest) -> entities.GetInfoResponse:
    return entities.GetInfoResponse(version=utils.version(), singleUserMode=auth_settings.is_single_user_mode)


@api_public.post("/track-event")
async def api_track_event_public(body: str = fastapi.Body(...)) -> entities.TrackEventResponse:
    # see comment on process_api_track
    return await process_api_track(body, user_id=None)


##############
# Private APIs
##############


# dummy endpoint to trigger auth refresh on the client side
@api_private.post("/refresh-auth")
async def api_refresh_auth(request: entities.RefreshAuthRequest, user: User) -> entities.RefreshAuthResponse:
    return entities.RefreshAuthResponse()


@api_private.post("/get-user")
async def api_get_user(request: entities.GetUserRequest, user: User) -> entities.GetUserResponse:
    return entities.GetUserResponse(userId=user.id)


@api_private.post("/get-feeds")
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


@api_private.post("/get-last-entries")
async def api_get_last_entries(request: entities.GetLastEntriesRequest, user: User) -> entities.GetLastEntriesResponse:
    linked_feeds = await fl_domain.get_linked_feeds(user.id)

    linked_feeds_ids = [link.feed_id for link in linked_feeds]

    entries = await l_domain.get_entries_by_filter_with_fallback(
        feeds_ids=linked_feeds_ids,
        period=request.period,
        limit=settings.max_returned_entries,
        fallback_limit=settings.news_outside_period,
    )

    external_entries, tags_mapping = await _external_entries(
        entries, with_body=False, user_id=user.id, min_tag_count=request.minTagCount
    )

    return entities.GetLastEntriesResponse(entries=external_entries, tagsMapping=tags_mapping)


@api_private.post("/create-or-update-rule")
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


@api_private.post("/delete-rule")
async def api_delete_rule(request: entities.DeleteRuleRequest, user: User) -> entities.DeleteRuleResponse:
    await s_domain.delete_rule(user_id=user.id, rule_id=request.id)

    return entities.DeleteRuleResponse()


@api_private.post("/update-rule")
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


@api_private.post("/get-rules")
async def api_get_rules(request: entities.GetRulesRequest, user: User) -> entities.GetRulesResponse:
    rules = await s_domain.get_rules_for_user(user_id=user.id)

    external_rules = await _prepare_rules(rules)

    return entities.GetRulesResponse(rules=external_rules)


@api_private.post("/get-score-details")
async def api_get_score_details(
    request: entities.GetScoreDetailsRequest, user: User
) -> entities.GetScoreDetailsResponse:
    entry_id = request.entryId

    rules = await s_domain.get_rules_for_user(user.id)

    tags_ids = await o_domain.get_tags_ids_for_entries([entry_id])

    rules = s_domain.get_score_rules(rules, tags_ids.get(entry_id, set()))

    external_rules = await _prepare_rules(rules)

    return entities.GetScoreDetailsResponse(rules=external_rules)


@api_private.post("/set-marker")
async def api_set_marker(request: entities.SetMarkerRequest, user: User) -> entities.SetMarkerResponse:
    await m_domain.set_marker(user_id=user.id, entry_id=request.entryId, marker=request.marker.to_internal())

    return entities.SetMarkerResponse()


@api_private.post("/remove-marker")
async def api_remove_marker(request: entities.RemoveMarkerRequest, user: User) -> entities.RemoveMarkerResponse:
    await m_domain.remove_marker(user_id=user.id, entry_id=request.entryId, marker=request.marker.to_internal())

    return entities.RemoveMarkerResponse()


@api_private.post("/discover-feeds")
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


@api_private.post("/add-feed")
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


@api_private.post("/add-opml")
async def api_add_opml(request: entities.AddOpmlRequest, user: User) -> entities.AddOpmlResponse:
    from ffun.parsers import errors as p_errors

    try:
        feed_infos = p_domain.parse_opml(request.content)
    except p_errors.MalformedOPML:
        raise APIError(
            code="malformed_opml", message="The provided OPML file is malformed. Please check the file and try again."
        )

    await meta_domain.add_feeds(feed_infos, user.id)

    logger.business_event("opml_import", user_id=user.id, feeds_count=len(feed_infos))

    return entities.AddOpmlResponse()


@api_private.get("/get-opml")
async def api_get_opml(user: User) -> PlainTextResponse:
    linked_feeds = await fl_domain.get_linked_feeds(user.id)

    linked_feeds_ids = [link.feed_id for link in linked_feeds]

    feeds = await f_domain.get_feeds(ids=linked_feeds_ids)

    content = p_domain.create_opml(feeds=feeds)

    headers = {"Content-Disposition": "attachment; filename=feeds-fun.opml"}

    return PlainTextResponse(content=content, media_type="application/xml", headers=headers)


@api_private.post("/unsubscribe")
async def api_unsubscribe(request: entities.UnsubscribeRequest, user: User) -> entities.UnsubscribeResponse:
    await fl_domain.remove_link(user_id=user.id, feed_id=request.feedId)

    return entities.UnsubscribeResponse()


@api_private.post("/subscribe-to-collections")
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


@api_private.post("/get-resource-history")
async def api_get_resource_history(
    request: entities.GetResourceHistoryRequest, user: User
) -> entities.GetResourceHistoryResponse:
    history = await r_domain.load_resource_history(user_id=user.id, kind=request.kind.to_internal())

    return entities.GetResourceHistoryResponse(
        history=[entities.ResourceHistoryRecord.from_internal(resource) for resource in history]
    )


@api_private.post("/get-user-settings")
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


@api_private.post("/set-user-setting")
async def api_set_user_setting(request: entities.SetUserSettingRequest, user: User) -> entities.SetUserSettingResponse:
    await us_domain.save_setting(user_id=user.id, kind=request.kind.to_internal(), value=request.value)

    return entities.SetUserSettingResponse()


@api_private.post("/remove-user")
async def api_remove_user(
    request: fastapi.Request, _request: entities.RemoveUserRequest, user: User, response: fastapi.Response
) -> entities.RemoveUserResponse:
    await a_domain.logout_user_from_all_sessions(user_id=user.id)

    await dp_domain.remove_user(user_id=user.id)

    # remove all cookies to force client to detect that user is logged out
    # also it ensures that consent cookies dialog is shown again
    for cookie in request.cookies:
        response.delete_cookie(cookie)

    return entities.RemoveUserResponse()


@api_private.post("/track-event")
async def api_track_event_private(user: User, body: str = fastapi.Body(...)) -> entities.TrackEventResponse:
    # see comment on process_api_track
    return await process_api_track(body, user_id=user.id)


@api_private.post("/get-entries-by-ids")
async def api_get_entries_by_ids_private(
    request: entities.GetEntriesByIdsRequest, user: User
) -> entities.GetEntriesByIdsResponse:
    return await process_api_get_entries(request, user_id=user.id)


#######################
# Swagger documentation
#######################

swagger_ui_api_parameters: dict[str, Any] = {
    "defaultModelsExpandDepth": -1,
    "defaultModelExpandDepth": 10,
}


swagger_title = "Feeds Fun SPA API"


swagger_description = """
Greetings!

Welcome to the documentation for the Feeds Fun Single Page Application (SPA) API.

**This API is solely intended for use by the Feeds Fun SPA frontend.**

Please note that the project is currently in its early stages of development, and as such, \
the API may undergo significant changes. We appreciate your understanding and patience during this phase.

At present, our **documentation does not include information regarding authentication**. \
If you are interested in using this API, the best way to get started \
is to give our SPA handle authentication for you.

For additional resources, please visit the following links:

- [Feeds Fun Website](https://feeds.fun)
- [Feeds Fun Blog](https://blog.feeds.fun)
- [GitHub Repository](https://github.com/Tiendil/feeds.fun)

Thank you for your interest in the Feeds Fun. We look forward to your contributions and feedback.

"""


@api_docs.get("/openapi.json", include_in_schema=False)
async def openapi(request: fastapi.Request) -> JSONResponse:
    content = get_openapi(
        title="Feeds Fun SPA API",
        version=metadata.version("ffun"),
        description=swagger_description,
        routes=request.app.routes,
    )

    return JSONResponse(content=content)


@api_docs.get("/", include_in_schema=False)
async def docs(request: fastapi.Request) -> HTMLResponse:
    openapi_url = request.scope.get("root_path", "") + "/spa/docs/openapi.json"

    return get_swagger_ui_html(
        openapi_url=openapi_url, title=swagger_title, swagger_ui_parameters=swagger_ui_api_parameters
    )
