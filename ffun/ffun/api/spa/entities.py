import copy
import datetime
import enum
from decimal import Decimal
from typing import Callable, Iterable

import pydantic

from ffun.api.spa import front_events
from ffun.core import api
from ffun.core.entities import BaseEntity
from ffun.domain.entities import (
    AbsoluteUrl,
    CollectionId,
    CollectionSlug,
    EntryId,
    FeedId,
    FeedUrl,
    RuleId,
    TagId,
    TagUid,
    UnknownUrl,
    UserId,
)
from ffun.entitlements import domain as en_domain
from ffun.entitlements import entities as en_entities
from ffun.feeds import entities as f_entities
from ffun.feeds_collections import entities as fc_entities
from ffun.library import entities as l_entities
from ffun.llms_framework import domain as llms_domain
from ffun.llms_framework.entities import LLMCostPoints
from ffun.markers import entities as m_entities
from ffun.ontology import entities as o_entities
from ffun.parsers import entities as p_entities
from ffun.product import entities as product_entities
from ffun.resources import entities as r_entities
from ffun.scores import entities as s_entities
from ffun.subscriptions import entities as sub_entities
from ffun.tags import entities as t_entities
from ffun.user_settings import domain as us_domain
from ffun.user_settings import entities as us_entities


class Marker(enum.IntEnum):
    read = 1
    can_see_tags = 2

    @classmethod
    def from_internal(cls, marker: m_entities.Marker) -> "Marker":
        return cls(marker.value)


class MutableMarker(enum.IntEnum):
    read = Marker.read

    def to_internal(self) -> m_entities.Marker:
        return m_entities.Marker(self.value)


class Feed(BaseEntity):
    id: FeedId
    title: str | None
    description: str | None
    url: FeedUrl
    siteUrl: AbsoluteUrl | None = None
    state: str
    lastError: str | None = None
    loadedAt: datetime.datetime | None
    linkedAt: datetime.datetime | None
    collectionIds: list[CollectionId]
    young: bool
    entriesPerDay: int
    entriesLoadedDetails: list[int] | None = None

    @classmethod
    def from_internal(  # noqa: CFQ002
        cls,
        feed: f_entities.Feed,
        linked_at: datetime.datetime | None,
        collection_ids: list[CollectionId],
        young: bool,
        entries_per_day: int,
        entries_loaded_details: list[int] | None = None,
    ) -> "Feed":
        return cls(
            id=feed.id,
            title=feed.title,
            description=feed.description,
            url=feed.url,
            siteUrl=feed.site_url,
            state=feed.state.name,
            lastError=feed.last_error.name if feed.last_error else None,
            loadedAt=feed.loaded_at,
            linkedAt=linked_at,
            collectionIds=collection_ids,
            young=young,
            entriesPerDay=entries_per_day,
            entriesLoadedDetails=entries_loaded_details,
        )


class ReferenceKind(enum.StrEnum):
    unknown = "unknown"
    author = "author"
    comments = "comments"
    page = "page"
    video = "video"
    audio = "audio"
    image = "image"
    document = "document"


REFERENCE_KIND_MAPPING: dict[l_entities.ReferenceKind, ReferenceKind] = {
    reference: ReferenceKind(reference.name) for reference in l_entities.ReferenceKind
}


class Reference(BaseEntity):
    kind: ReferenceKind
    url: AbsoluteUrl
    title: str | None = None
    mime_type: str | None = None
    width: int | None = None
    height: int | None = None
    duration: datetime.timedelta | None = None
    size: int | None = None
    extra: dict[str, int | float | str | None] | None = None

    @pydantic.model_serializer(mode="wrap")
    def serialize_model(self, handler: Callable[["Reference"], dict[str, object | None]]) -> dict[str, object]:
        data = handler(self)
        return {key: value for key, value in data.items() if value is not None}

    @classmethod
    def from_internal(cls, reference: l_entities.Reference) -> "Reference":
        return cls(
            kind=REFERENCE_KIND_MAPPING[reference.kind],
            url=reference.url,
            title=reference.title,
            mime_type=reference.mime_type,
            width=reference.width,
            height=reference.height,
            duration=reference.duration,
            size=reference.size,
            extra=copy.deepcopy(reference.extra) if reference.extra is not None else None,
        )


class Entry(BaseEntity):
    id: EntryId
    title: str
    url: AbsoluteUrl
    tags: list[TagId]
    markers: list[Marker] = []
    score: int
    scoreContributions: dict[TagId, int]
    publishedAt: datetime.datetime
    body: str | None = None
    references: list[Reference] | None = None

    @classmethod
    def from_internal(  # noqa: CFQ002
        cls,
        entry: l_entities.Entry,
        tags: Iterable[TagId],
        markers: Iterable[Marker],
        score: int,
        score_contributions: dict[TagId, int],
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
            # THIS IS AN INTENDED BEHAVIOR
            # we set publishedAt for the frontend as global entry creation time
            # because it is the only reliable time with "published" meaning
            # actual published_at is absolutely unreliable because comes from the third-party sources
            # and can be broken in numerous ways.
            publishedAt=entry.created_at,
            # Some APIs return full entry info, some return shorter info to save traffic and speed up the response.
            body=entry.body if with_body else None,
            references=[Reference.from_internal(reference) for reference in entry.references] if with_body else None,
        )


class Rule(BaseEntity):
    id: RuleId
    requiredTags: list[TagUid]
    excludedTags: list[TagUid]
    score: int
    createdAt: datetime.datetime
    updatedAt: datetime.datetime

    @classmethod
    def from_internal(cls, rule: s_entities.Rule, tags_mapping: dict[TagId, TagUid]) -> "Rule":
        return cls(
            id=rule.id,
            requiredTags=[tags_mapping[tag_id] for tag_id in rule.required_tags],
            excludedTags=[tags_mapping[tag_id] for tag_id in rule.excluded_tags],
            score=rule.score,
            createdAt=rule.created_at,
            updatedAt=rule.updated_at,
        )


class EntryInfo(BaseEntity):
    title: str
    body: str
    url: AbsoluteUrl | None
    published_at: datetime.datetime

    @classmethod
    def from_internal(cls, entry: p_entities.EntryInfo) -> "EntryInfo":
        return cls(title=entry.title, body=entry.body, url=entry.external_url, published_at=entry.published_at)


class FeedInfo(BaseEntity):
    url: FeedUrl
    siteUrl: AbsoluteUrl | None = None
    title: str
    description: str
    isLinked: bool

    entries: list[EntryInfo]

    @classmethod
    def from_internal(cls, feed: p_entities.FeedInfo, is_linked: bool) -> "FeedInfo":
        return cls(
            url=feed.url,
            siteUrl=feed.site_url,
            title=feed.title,
            description=feed.description,
            isLinked=is_linked,
            entries=[EntryInfo.from_internal(entry) for entry in feed.entries],
        )


class TagInfo(BaseEntity):
    uid: str
    name: str
    link: str | None
    categories: set[t_entities.TagCategory]

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

    view_news_filter_interval = "view_news_filter_interval"
    view_news_filter_sort_by = "view_news_filter_sort_by"
    view_news_filter_min_tags_count = "view_news_filter_min_tags_count"
    view_news_filter_show_read = "view_news_filter_show_read"

    view_feeds_feed_order = "view_feeds_feed_order"
    view_feeds_failed_feeds_first = "view_feeds_failed_feeds_first"

    view_rules_order = "view_rules_order"

    show_sidebar = "show_sidebar"

    @classmethod
    def from_internal(cls, kind: us_entities.SettingKind) -> "UserSettingKind":
        real_kind = product_entities.UserSetting(int(kind))
        return UserSettingKind(real_kind.name)

    def to_internal(self) -> us_entities.SettingKind:
        value: object = getattr(product_entities.UserSetting, self.name)
        assert isinstance(value, int)
        return us_entities.SettingKind(value)


class UserSetting(BaseEntity):
    kind: UserSettingKind
    type: us_entities.TypeId  # should not differ between front & back => no need to convert
    value: object
    name: str

    @classmethod
    def from_internal(cls, kind: us_entities.SettingKind, value: str | int | float | bool) -> "UserSetting":
        real_setting = us_domain.setting(kind)

        return cls(
            kind=UserSettingKind.from_internal(kind),
            type=real_setting.type.id,
            value=real_setting.type.normalize(value),
            name=real_setting.name,
        )


class ResourceKind(enum.StrEnum):
    tokens_cost = "tokens_cost"
    day_token_usage = "day_token_usage"  # noqa: S105
    month_token_usage = "month_token_usage"  # noqa: S105
    lifetime_token_usage = "lifetime_token_usage"  # noqa: S105

    @classmethod
    def from_internal(cls, kind: int) -> "ResourceKind":
        real_kind = product_entities.Resource(kind)
        return ResourceKind(real_kind.name)

    def to_internal(self) -> r_entities.ResourceKind:
        value: object = getattr(product_entities.Resource, self.name)
        assert isinstance(value, int)
        return r_entities.ResourceKind(value)

    def amount_from_internal(self, amount: int) -> Decimal:
        if self == ResourceKind.tokens_cost:
            return Decimal(llms_domain.cost_points_to_usd_cost(LLMCostPoints(amount)))

        return Decimal(amount)


class EntitlementKind(enum.StrEnum):
    day_tokens = "day_tokens"  # noqa: S105
    month_tokens = "month_tokens"  # noqa: S105
    lifetime_tokens = "lifetime_tokens"  # noqa: S105

    @classmethod
    def from_internal(cls, kind: en_entities.EntitlementKindId) -> "EntitlementKind":
        return cls(kind.name)

    def to_internal(self) -> en_entities.EntitlementKindId:
        return en_entities.EntitlementKindId[self.name]


class TokenKind(enum.StrEnum):
    day = "day"
    month = "month"
    lifetime = "lifetime"

    @classmethod
    def from_internal(cls, kind: product_entities.Credit) -> "TokenKind":
        return cls[kind.name]


class ProductStateEntitlement(pydantic.BaseModel):
    granted: bool
    value: int | None
    startsAt: datetime.datetime | None
    expiresAt: datetime.datetime | None

    @classmethod
    def from_internal(
        cls,
        entitlement: en_entities.EffectiveEntitlementInterval | None,
    ) -> "ProductStateEntitlement":
        is_lifetime = entitlement is not None and en_domain.get_entitlement_kind(entitlement.kind_id).is_lifetime

        return cls(
            granted=entitlement is not None,
            value=entitlement.value if entitlement is not None else None,
            startsAt=entitlement.starts_at if entitlement is not None else None,
            expiresAt=entitlement.expires_at if entitlement is not None and not is_lifetime else None,
        )


class ProductStateToken(pydantic.BaseModel):
    limit: int | None
    balance: int
    periodStartsAt: datetime.datetime | None
    periodEndsAt: datetime.datetime | None

    @classmethod
    def from_internal(
        cls,
        *,
        entitlement: en_entities.EffectiveEntitlementInterval | None,
        resource: r_entities.Resource,
        period_started_at: datetime.datetime | None,
        period_ends_at: datetime.datetime | None,
    ) -> "ProductStateToken":
        is_lifetime = entitlement is not None and en_domain.get_entitlement_kind(entitlement.kind_id).is_lifetime

        return cls(
            limit=entitlement.value if entitlement is not None and not is_lifetime else None,
            balance=max(entitlement.value - resource.total, 0) if entitlement is not None else 0,
            periodStartsAt=period_started_at,
            periodEndsAt=period_ends_at,
        )


class SubscriptionStatus(enum.StrEnum):
    pending = "pending"
    trialing = "trialing"
    active = "active"
    past_due = "past_due"
    paused = "paused"
    ended = "ended"

    @classmethod
    def from_internal(cls, status: sub_entities.SubscriptionStatusId) -> "SubscriptionStatus":
        return cls[status.name]


class ProductStateSubscription(pydantic.BaseModel):
    status: SubscriptionStatus
    startedAt: datetime.datetime
    periodStartsAt: datetime.datetime
    periodEndsAt: datetime.datetime
    expectedRenewalAt: datetime.datetime | None
    endsAt: datetime.datetime | None

    @classmethod
    def from_internal(cls, subscription: sub_entities.Subscription) -> "ProductStateSubscription":
        return cls(
            status=SubscriptionStatus.from_internal(subscription.status),
            startedAt=subscription.started_at,
            periodStartsAt=subscription.period_starts_at,
            periodEndsAt=subscription.period_ends_at,
            expectedRenewalAt=subscription.expected_renewal_at,
            endsAt=subscription.ends_at,
        )


class ResourceStatisticsInterval(enum.StrEnum):
    day = "day"
    month = "month"
    year = "year"

    def to_internal(self) -> r_entities.ResourceStatisticsInterval:
        return r_entities.ResourceStatisticsInterval(self.value)


class ResourceHistoryRecord(pydantic.BaseModel):
    intervalStartedAt: datetime.datetime
    used: Decimal
    reserved: Decimal

    @classmethod
    def from_internal(cls, record: r_entities.Resource) -> "ResourceHistoryRecord":
        kind = ResourceKind.from_internal(record.kind)

        return cls(
            intervalStartedAt=record.interval_started_at,
            used=kind.amount_from_internal(record.used),
            reserved=kind.amount_from_internal(record.reserved),
        )


class ResourceStatisticsSeries(pydantic.BaseModel):
    firstDate: datetime.date
    values: list[Decimal]

    @classmethod
    def from_internal(
        cls,
        *,
        kind: ResourceKind,
        series: r_entities.ResourceStatisticsSeries,
    ) -> "ResourceStatisticsSeries":
        return cls(
            firstDate=series.first_date,
            values=[kind.amount_from_internal(value) for value in series.values],
        )


class Collection(pydantic.BaseModel):
    id: CollectionId
    slug: CollectionSlug
    guiOrder: int
    name: str
    description: str
    feedsNumber: int
    showOnMain: bool

    @classmethod
    def from_internal(cls, record: fc_entities.Collection) -> "Collection":
        return cls(
            id=record.id,
            slug=record.slug,
            guiOrder=record.gui_order,
            name=record.name,
            description=record.description,
            feedsNumber=len(record.feeds),
            showOnMain=record.show_on_main,
        )


class CollectionFeedInfo(pydantic.BaseModel):
    url: FeedUrl
    title: str
    description: str
    id: f_entities.FeedId

    @classmethod
    def from_internal(cls, record: fc_entities.FeedInfo) -> "CollectionFeedInfo":
        assert record.feed_id is not None
        return cls(url=record.url, title=record.title, description=record.description, id=record.feed_id)


class IntegrationInfo(pydantic.BaseModel):
    name: str
    discovery: bool
    postprocessing: bool


##################
# Request/Response
##################


class GetFeedsRequest(api.APIRequest):
    pass


class GetFeedsResponse(api.APISuccess):
    feeds: list[Feed]


class GetFeedsByIdsRequest(api.APIRequest):
    ids: list[FeedId]


class GetFeedsByIdsResponse(api.APISuccess):
    feeds: list[Feed]


class GetLastEntriesRequest(api.APIRequest):
    period: datetime.timedelta | None = None
    minTagCount: int = 2  # TODO: remove default after 1.21 branch is released

    @pydantic.field_validator("period")
    def validate_period(cls, v: None | datetime.timedelta) -> None | datetime.timedelta:
        if v is not None and v.total_seconds() < 0:
            raise ValueError("period must be positive")
        return v


class GetLastEntriesResponse(api.APISuccess):
    entries: list[Entry]
    tagsMapping: dict[TagId, TagUid]


class GetLastCollectionEntriesRequest(api.APIRequest):
    collectionSlug: CollectionSlug
    period: datetime.timedelta | None = None
    minTagCount: int = 2  # TODO: remove default after 1.21 branch is released

    @pydantic.field_validator("period")
    def validate_period(cls, v: None | datetime.timedelta) -> None | datetime.timedelta:
        if v is not None and v.total_seconds() < 0:
            raise ValueError("period must be positive")
        return v


class GetLastCollectionEntriesResponse(api.APISuccess):
    entries: list[Entry]
    tagsMapping: dict[TagId, TagUid]


class GetEntriesByIdsRequest(api.APIRequest):
    ids: list[EntryId]


class GetEntriesByIdsResponse(api.APISuccess):
    entries: list[Entry]
    tagsMapping: dict[TagId, TagUid]


class CreateOrUpdateRuleRequest(api.APIRequest):
    requiredTags: list[TagUid]
    excludedTags: list[TagUid]
    score: int


class CreateOrUpdateRuleResponse(api.APISuccess):
    pass


class DeleteRuleRequest(api.APIRequest):
    id: RuleId


class DeleteRuleResponse(api.APISuccess):
    pass


class UpdateRuleRequest(api.APIRequest):
    id: RuleId
    requiredTags: list[TagUid]
    excludedTags: list[TagUid]
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
    marker: MutableMarker


class SetMarkerResponse(api.APISuccess):
    pass


class RemoveMarkerRequest(api.APIRequest):
    entryId: EntryId
    marker: MutableMarker


class RemoveMarkerResponse(api.APISuccess):
    pass


class DiscoverFeedsRequest(api.APIRequest):
    url: UnknownUrl


class DiscoverFeedsResponse(api.APISuccess):
    feeds: list[FeedInfo]


class AddFeedRequest(api.APIRequest):
    url: UnknownUrl


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


class GetIntegrationsRequest(api.APIRequest):
    pass


class GetIntegrationsResponse(api.APISuccess):
    integrations: list[IntegrationInfo]


class SubscribeToCollectionsRequest(api.APIRequest):
    collections: list[fc_entities.CollectionId]


class SubscribeToCollectionsResponse(api.APISuccess):
    pass


class GetTagsInfoRequest(api.APIRequest):
    uids: set[TagUid]


class GetTagsInfoResponse(api.APISuccess):
    tags: dict[TagUid, TagInfo]


class GetUserSettingsRequest(api.APIRequest):
    pass


class GetUserSettingsResponse(api.APISuccess):
    settings: list[UserSetting]


class SetUserSettingRequest(api.APIRequest):
    kind: UserSettingKind
    value: object

    @pydantic.model_validator(mode="before")
    @classmethod
    def validate_value(cls, values: dict[str, object]) -> dict[str, object]:
        raw_kind = values.get("kind")

        assert isinstance(raw_kind, str), "kind must be a string"

        kind = UserSettingKind(raw_kind).to_internal()
        value = values.get("value")

        real_setting = us_domain.setting(kind)
        values["value"] = real_setting.type.normalize(value)

        return values


class SetUserSettingResponse(api.APISuccess):
    pass


class GetResourceHistoryRequest(api.APIRequest):
    kind: ResourceKind


class GetResourceHistoryResponse(api.APISuccess):
    history: list[ResourceHistoryRecord]


class GetResourceStatisticsRequest(api.APIRequest):
    kinds: list[ResourceKind]
    interval: ResourceStatisticsInterval


class GetResourceStatisticsResponse(api.APISuccess):
    interval: ResourceStatisticsInterval
    statistics: dict[ResourceKind, ResourceStatisticsSeries]


class GetInfoRequest(api.APIRequest):
    pass


class GetInfoResponse(api.APISuccess):
    version: str
    singleUserMode: bool


class TrackEventRequest(api.APIRequest):
    event: front_events.Event


class TrackEventResponse(api.APISuccess):
    pass


class RemoveUserRequest(api.APIRequest):
    pass


class RemoveUserResponse(api.APISuccess):
    pass


class RefreshAuthRequest(api.APIRequest):
    pass


class RefreshAuthResponse(api.APISuccess):
    pass


class GetUserRequest(api.APIRequest):
    pass


class GetUserResponse(api.APISuccess):
    userId: UserId


class GetProductStateRequest(api.APIRequest):
    pass


class GetProductStateResponse(api.APISuccess):
    subscriptions: list[ProductStateSubscription]
    entitlements: dict[EntitlementKind, ProductStateEntitlement]
    tokens: dict[TokenKind, ProductStateToken]
