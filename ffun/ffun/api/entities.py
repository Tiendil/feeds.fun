import datetime
import enum
import uuid
from decimal import Decimal
from typing import Any, Iterable

import markdown
import pydantic

from ffun.api import front_events
from ffun.core import api
from ffun.core.entities import BaseEntity
from ffun.domain.entities import EntryId, FeedId, UserId
from ffun.feeds import entities as f_entities
from ffun.feeds_collections import entities as fc_entities
from ffun.feeds_links import entities as fl_entities
from ffun.library import entities as l_entities

# TODO: rename to public name
from ffun.llms_framework.keys_rotator import USDCost, _cost_points
from ffun.markers import entities as m_entities
from ffun.ontology import entities as o_entities
from ffun.parsers import entities as p_entities
from ffun.resources import entities as r_entities
from ffun.scores import entities as s_entities
from ffun.user_settings import types as us_types
from ffun.user_settings.values import user_settings


class Marker(enum.StrEnum):
    read = "read"

    @classmethod
    def from_internal(cls, marker: m_entities.Marker) -> "Marker":
        return cls(marker.name)

    def to_internal(self) -> m_entities.Marker:
        return m_entities.Marker[self.value]


class Feed(BaseEntity):
    id: FeedId
    title: str | None
    description: str | None
    url: str
    state: str
    lastError: str | None = None
    loadedAt: datetime.datetime | None
    linkedAt: datetime.datetime | None
    collectionIds: list[fc_entities.CollectionId]

    @classmethod
    def from_internal(
        cls, feed: f_entities.Feed, link: fl_entities.FeedLink, collection_ids: list[fc_entities.CollectionId]
    ) -> "Feed":
        return cls(
            id=feed.id,
            title=feed.title,
            description=feed.description,
            url=feed.url,
            state=feed.state.name,
            lastError=feed.last_error.name if feed.last_error else None,
            loadedAt=feed.loaded_at,
            linkedAt=link.created_at,
            collectionIds=collection_ids,
        )


class Entry(BaseEntity):
    id: EntryId
    title: str
    url: str
    tags: list[int]
    markers: list[Marker] = []
    score: int
    scoreContributions: dict[int, int]
    publishedAt: datetime.datetime
    catalogedAt: datetime.datetime
    body: str | None = None

    @classmethod
    def from_internal(  # noqa: CFQ002
        cls,
        entry: l_entities.Entry,
        tags: Iterable[int],
        markers: Iterable[Marker],
        score: int,
        score_contributions: dict[int, int],
        with_body: bool = False,
    ) -> "Entry":
        return cls(
            id=entry.id,
            title=entry.title,
            url=entry.external_url,
            tags=list(tags),
            markers=list(markers),
            score=score,
            scoreContributions=score_contributions,
            publishedAt=entry.published_at,
            catalogedAt=entry.cataloged_at,
            body=entry.body if with_body else None,
        )


class Rule(BaseEntity):
    id: uuid.UUID
    tags: list[str]
    score: int
    createdAt: datetime.datetime
    updatedAt: datetime.datetime

    @classmethod
    def from_internal(cls, rule: s_entities.Rule, tags_mapping: dict[int, str]) -> "Rule":
        return cls(
            id=rule.id,
            tags=[tags_mapping[tag_id] for tag_id in rule.tags],
            score=rule.score,
            createdAt=rule.created_at,
            updatedAt=rule.updated_at,
        )


class EntryInfo(BaseEntity):
    title: str
    body: str
    url: str | None
    published_at: datetime.datetime

    @classmethod
    def from_internal(cls, entry: p_entities.EntryInfo) -> "EntryInfo":
        return cls(title=entry.title, body=entry.body, url=entry.external_url, published_at=entry.published_at)


class FeedInfo(BaseEntity):
    url: str
    title: str
    description: str

    entries: list[EntryInfo]

    @classmethod
    def from_internal(cls, feed: p_entities.FeedInfo) -> "FeedInfo":
        return cls(
            url=feed.url,
            title=feed.title,
            description=feed.description,
            entries=[EntryInfo.from_internal(entry) for entry in feed.entries],
        )


class TagInfo(BaseEntity):
    uid: str
    name: str
    link: str | None
    categories: set[o_entities.TagCategory]

    @classmethod
    def from_internal(cls, tag: o_entities.Tag, uid: str) -> "TagInfo":
        assert tag.name is not None

        return cls(uid=uid, name=tag.name, link=tag.link, categories=tag.categories)


class UserSettingKind(enum.StrEnum):
    openai_api_key = "openai_api_key"
    gemini_api_key = "gemini_api_key"

    hide_message_about_setting_up_key = "hide_message_about_setting_up_key"
    hide_message_about_adding_collections = "hide_message_about_adding_collections"
    hide_message_check_your_feed_urls = "hide_message_check_your_feed_urls"
    process_entries_not_older_than = "process_entries_not_older_than"
    max_tokens_cost_in_month = "max_tokens_cost_in_month"

    @classmethod
    def from_internal(cls, kind: int) -> "UserSettingKind":
        from ffun.application.user_settings import UserSetting

        real_kind = UserSetting(kind)
        return UserSettingKind(real_kind.name)

    def to_internal(self) -> int:
        from ffun.application.user_settings import UserSetting

        return getattr(UserSetting, self.name)  # type: ignore


class UserSetting(BaseEntity):
    kind: UserSettingKind
    type: us_types.TypeId  # should not differ between front & back => no need to convert
    value: Any
    name: str
    description: str | None

    @classmethod
    def from_internal(cls, kind: int, value: str | int | float | bool) -> "UserSetting":
        from ffun.application.user_settings import UserSetting

        real_kind = UserSetting(kind)

        real_setting = user_settings.get(real_kind)

        assert real_setting is not None

        return cls(
            kind=UserSettingKind.from_internal(real_kind),
            type=real_setting.type.id,
            value=real_setting.type.normalize(value),
            name=real_setting.name,
            description=markdown.markdown(real_setting.description) if real_setting.description else None,
        )


class ResourceKind(enum.StrEnum):
    tokens_cost = "tokens_cost"

    @classmethod
    def from_internal(cls, kind: int) -> "ResourceKind":
        from ffun.application.resources import Resource

        real_kind = Resource(kind)
        return ResourceKind(real_kind.name)

    def to_internal(self) -> int:
        from ffun.application.resources import Resource

        return getattr(Resource, self.name)  # type: ignore


class ResourceHistoryRecord(pydantic.BaseModel):
    intervalStartedAt: datetime.datetime
    used: Decimal
    reserved: Decimal

    @classmethod
    def from_internal(cls, record: r_entities.Resource) -> "ResourceHistoryRecord":
        from ffun.application.resources import Resource

        if record.kind == Resource.tokens_cost:
            transformer = _cost_points.to_cost
        else:

            def transformer(points: int) -> USDCost:
                return USDCost(Decimal(points))

        return cls(
            intervalStartedAt=record.interval_started_at,
            used=transformer(record.used),
            reserved=transformer(record.reserved),
        )


class Collection(pydantic.BaseModel):
    id: fc_entities.CollectionId
    guiOrder: int
    name: str
    description: str
    feedsNumber: int

    @classmethod
    def from_internal(cls, record: fc_entities.Collection) -> "Collection":
        return cls(
            id=record.id,
            guiOrder=record.gui_order,
            name=record.name,
            description=record.description,
            feedsNumber=len(record.feeds),
        )


class CollectionFeedInfo(pydantic.BaseModel):
    url: str
    title: str
    description: str
    id: f_entities.FeedId

    @classmethod
    def from_internal(cls, record: fc_entities.FeedInfo) -> "CollectionFeedInfo":
        assert record.feed_id is not None
        return cls(url=record.url, title=record.title, description=record.description, id=record.feed_id)


##################
# Request/Response
##################


class GetFeedsRequest(api.APIRequest):
    pass


class GetFeedsResponse(api.APISuccess):
    feeds: list[Feed]


class GetLastEntriesRequest(api.APIRequest):
    period: datetime.timedelta | None = None

    @pydantic.field_validator("period")
    def validate_period(cls, v: None | datetime.timedelta) -> None | datetime.timedelta:
        if v is not None and v.total_seconds() < 0:
            raise ValueError("period must be positive")
        return v


class GetLastEntriesResponse(api.APISuccess):
    entries: list[Entry]
    tagsMapping: dict[int, str]


class GetEntriesByIdsRequest(api.APIRequest):
    ids: list[EntryId]


class GetEntriesByIdsResponse(api.APISuccess):
    entries: list[Entry]
    tagsMapping: dict[int, str]


class CreateOrUpdateRuleRequest(api.APIRequest):
    tags: list[str]
    score: int


class CreateOrUpdateRuleResponse(api.APISuccess):
    pass


class DeleteRuleRequest(api.APIRequest):
    id: uuid.UUID


class DeleteRuleResponse(api.APISuccess):
    pass


class UpdateRuleRequest(api.APIRequest):
    id: uuid.UUID
    tags: list[str]
    score: int


class UpdateRuleResponse(api.APISuccess):
    pass


class GetRulesRequest(api.APIRequest):
    pass


class GetRulesResponse(api.APISuccess):
    rules: list[Rule]


class GetScoreDetailsRequest(api.APIRequest):
    entryId: EntryId


class GetScoreDetailsResponse(api.APISuccess):
    rules: list[Rule]


class SetMarkerRequest(api.APIRequest):
    entryId: EntryId
    marker: Marker


class SetMarkerResponse(api.APISuccess):
    pass


class RemoveMarkerRequest(api.APIRequest):
    entryId: EntryId
    marker: Marker


class RemoveMarkerResponse(api.APISuccess):
    pass


class DiscoverFeedsRequest(api.APIRequest):
    url: str


class DiscoverFeedsResponse(api.APISuccess):
    feeds: list[FeedInfo]


class AddFeedRequest(api.APIRequest):
    url: str


class AddFeedResponse(api.APISuccess):
    feed: Feed


class AddOpmlRequest(api.APIRequest):
    content: str


class AddOpmlResponse(api.APISuccess):
    pass


class UnsubscribeRequest(api.APIRequest):
    feedId: f_entities.FeedId


class UnsubscribeResponse(api.APISuccess):
    pass


class GetFeedsCollectionsRequest(api.APIRequest):
    pass


class GetFeedsCollectionsResponse(api.APISuccess):
    collections: list[Collection]


class GetCollectionFeedsRequest(api.APIRequest):
    collectionId: fc_entities.CollectionId


class GetCollectionFeedsResponse(api.APISuccess):
    feeds: list[CollectionFeedInfo]


class SubscribeToCollectionsRequest(api.APIRequest):
    collections: list[fc_entities.CollectionId]


class SubscribeToCollectionsResponse(api.APISuccess):
    pass


class GetTagsInfoRequest(api.APIRequest):
    uids: set[str]


class GetTagsInfoResponse(api.APISuccess):
    tags: dict[str, TagInfo]


class GetUserSettingsRequest(api.APIRequest):
    pass


class GetUserSettingsResponse(api.APISuccess):
    settings: list[UserSetting]


class SetUserSettingRequest(api.APIRequest):
    kind: UserSettingKind
    value: Any

    @pydantic.model_validator(mode="before")
    @classmethod
    def validate_value(cls, values: dict[str, Any]) -> dict[str, Any]:
        from ffun.application.user_settings import UserSetting

        kind = UserSettingKind(values["kind"]).to_internal()
        value = values.get("value")

        real_kind = UserSetting(kind)

        real_setting = user_settings.get(real_kind)

        values["value"] = real_setting.type.normalize(value)

        return values


class SetUserSettingResponse(api.APISuccess):
    pass


class GetResourceHistoryRequest(api.APIRequest):
    kind: ResourceKind


class GetResourceHistoryResponse(api.APISuccess):
    history: list[ResourceHistoryRecord]


class GetInfoRequest(api.APIRequest):
    pass


class GetInfoResponse(api.APISuccess):
    userId: UserId


class TrackEventRequest(api.APIRequest):
    event: front_events.Event


class TrackEventResponse(api.APISuccess):
    pass
