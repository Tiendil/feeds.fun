import datetime
import enum
import uuid
from typing import Any, Iterable

import markdown
import pydantic
from ffun.core import api
from ffun.feeds import entities as f_entities
from ffun.feeds_collections import entities as fc_entities
from ffun.library import entities as l_entities
from ffun.markers import entities as m_entities
from ffun.ontology import entities as o_entities
from ffun.parsers import entities as p_entities
from ffun.scores import entities as s_entities
from ffun.user_settings import types as us_types
from ffun.user_settings.values import user_settings


class Marker(str, enum.Enum):
    read = 'read'

    @classmethod
    def from_internal(cls, marker: m_entities.Marker) -> 'Marker':
        return cls(marker.name)

    def to_internal(self) -> m_entities.Marker:
        return m_entities.Marker[self.value]


class Feed(api.Base):
    id: uuid.UUID
    title: str|None
    description: str|None
    url: str
    state: str
    lastError: str|None = None
    loadedAt: datetime.datetime|None

    @classmethod
    def from_internal(cls, feed: f_entities.Feed) -> 'Feed':
        return cls(
            id=feed.id,
            title=feed.title,
            description=feed.description,
            url=feed.url,
            state=feed.state.name,
            lastError=feed.last_error.name if feed.last_error else None,
            loadedAt=feed.loaded_at,
        )


class Entry(api.Base):
    id: uuid.UUID
    feed_id: uuid.UUID
    title: str
    url: str
    tags: list[str]
    markers: list[Marker] = []
    score: int
    publishedAt: datetime.datetime
    catalogedAt: datetime.datetime
    body: str|None = None

    @classmethod
    def from_internal(cls,
                      entry: l_entities.Entry,
                      tags: Iterable[str],
                      markers: Iterable[Marker],
                      score: int,
                      with_body: bool = False) -> 'Entry':
        return cls(
            id=entry.id,
            feed_id=entry.feed_id,
            title=entry.title,
            url=entry.external_url,
            tags=list(tags),
            markers=list(markers),
            score=score,
            publishedAt=entry.published_at,
            catalogedAt=entry.cataloged_at,
            body=entry.body if with_body else None
        )


class Rule(api.Base):
    id: uuid.UUID
    tags: list[str]
    score: int
    createdAt: datetime.datetime

    @classmethod
    def from_internal(cls, rule: s_entities.Rule, tags_mapping: dict[int, str]) -> 'Rule':
        return cls(
            id=rule.id,
            tags={tags_mapping[tag_id] for tag_id in rule.tags},
            score=rule.score,
            createdAt=rule.created_at,
        )


class EntryInfo(api.Base):
    title: str
    body: str
    url: str
    published_at: datetime.datetime

    @classmethod
    def from_internal(cls, entry: p_entities.EntryInfo) -> 'EntryInfo':
        return cls(title=entry.title,
                   body=entry.body,
                   url=entry.external_url,
                   published_at=entry.published_at)


class FeedInfo(api.Base):
    url: str
    base_url: str
    title: str
    description: str

    entries: list[EntryInfo]

    @classmethod
    def from_internal(cls, feed: p_entities.FeedInfo) -> 'FeedInfo':
        return cls(url=feed.url,
                   base_url=feed.base_url,
                   title=feed.title,
                   description=feed.description,
                   entries=[EntryInfo.from_internal(entry) for entry in feed.entries])


class TagInfo(api.Base):
    uid: str
    name: str
    link: str|None
    categories: set[o_entities.TagCategory]

    @classmethod
    def from_internal(cls, tag: o_entities.Tag, uid: str) -> 'TagInfo':
        return cls(uid=uid,
                   name=tag.name,
                   link=tag.link,
                   categories=tag.categories)


class UserSettingKind(str, enum.Enum):
    openai_api_key = 'openai_api_key'
    openai_max_tokens_in_month = 'openai_max_tokens_in_month'
    openai_hide_message_about_setting_up_key = 'openai_hide_message_about_setting_up_key'

    @classmethod
    def from_internal(cls, kind: int) -> 'UserSettingKind':
        from ffun.application.user_settings import UserSetting
        real_kind = UserSetting(kind)
        return UserSettingKind(real_kind.name)

    def to_internal(self) -> int:
        from ffun.application.user_settings import UserSetting
        return getattr(UserSetting, self.name)


class UserSetting(api.Base):
    kind: UserSettingKind
    type: us_types.TypeId  # should not differ between front & back => no need to convert
    value: Any
    name: str
    description: str|None

    @classmethod
    def from_internal(cls, kind: int, value: str|int|float|bool) -> 'UserSetting':
        from ffun.application.user_settings import UserSetting

        real_kind = UserSetting(kind)

        real_setting = user_settings.get(real_kind)

        return cls(kind=UserSettingKind.from_internal(real_kind),
                   type=real_setting.type.id,
                   value=real_setting.type.normalize(value),
                   name=real_setting.name,
                   description=markdown.markdown(real_setting.description) if real_setting.description else None)


##################
# Request/Response
##################

class GetFeedsRequest(api.APIRequest):
    pass


class GetFeedsResponse(api.APISuccess):
    feeds: list[Feed]


class GetLastEntriesRequest(api.APIRequest):
    period: datetime.timedelta|None = None

    @pydantic.validator('period')
    def validate_period(cls, v):
        if v is not None and v.total_seconds() < 0:
            raise ValueError('period must be positive')
        return v


class GetLastEntriesResponse(api.APISuccess):
    entries: list[Entry]


class GetEntriesByIdsRequest(api.APIRequest):
    ids: list[uuid.UUID]


class GetEntriesByIdsResponse(api.APISuccess):
    entries: list[Entry]


class CreateRuleRequest(api.APIRequest):
    tags: list[str]
    score: int


class CreateRuleResponse(api.APISuccess):
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
    entryId: uuid.UUID


class GetScoreDetailsResponse(api.APISuccess):
    rules: list[Rule]


class SetMarkerRequest(api.APIRequest):
    entryId: uuid.UUID
    marker: Marker


class SetMarkerResponse(api.APISuccess):
    pass


class RemoveMarkerRequest(api.APIRequest):
    entryId: uuid.UUID
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
    pass


class AddOpmlRequest(api.APIRequest):
    content: str


class AddOpmlResponse(api.APISuccess):
    pass


class UnsubscribeRequest(api.APIRequest):
    feedId: uuid.UUID


class UnsubscribeResponse(api.APISuccess):
    pass


class GetFeedsCollectionsRequest(api.APIRequest):
    pass


class GetFeedsCollectionsResponse(api.APISuccess):
    collections: list[fc_entities.Collection]


class SubscribeToFeedsCollectionsRequest(api.APIRequest):
    collections: list[fc_entities.Collection]


class SubscribeToFeedsCollectionsResponse(api.APISuccess):
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
    value: None|bool|int|str

    @pydantic.root_validator
    def validate_value(cls, values):
        from ffun.application.user_settings import UserSetting

        kind = values.get('kind').to_internal()
        value = values.get('value')

        real_kind = UserSetting(kind)

        real_setting = user_settings.get(real_kind)

        values['value'] = real_setting.type.normalize(value)

        return values


class SetUserSettingResponse(api.APISuccess):
    pass
