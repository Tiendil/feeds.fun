import enum
from typing import Annotated, Literal

import pydantic

from ffun.core.entities import BaseEntity
from ffun.domain.entities import EntryId

EventsViewName = Literal[
    "main", "news", "rules", "public_collections", "settings", "collections", "discovery", "feeds"
]


class NewsLinkOpened(BaseEntity):
    name: Literal["news_link_opened"]
    view: EventsViewName
    entry_id: EntryId


class NewsBodyOpened(BaseEntity):
    name: Literal["news_body_opened"]
    view: EventsViewName
    entry_id: EntryId


class SocialLinkClicked(BaseEntity):
    name: Literal["social_link_clicked"]
    view: EventsViewName
    link_type: Literal["api", "blog", "reddit", "discord", "github", "roadmap"]


# TODO: When refactoring events, consider merging AuthButtonClicked with ButtonClicked
# and AuthButtonType with ButtonType.
class AuthButtonType(enum.StrEnum):
    login = "login"
    join_ = "join"
    go_to_feeds = "go_to_feeds"
    register_toolbar = "register.toolbar"
    register_tags_filter = "register.tags_filter"


class AuthButtonClicked(BaseEntity):
    name: Literal["auth_button_clicked"]
    view: EventsViewName
    button_type: AuthButtonType


class ButtonType(enum.StrEnum):
    add_feed_toolbar = "add_feed.toolbar"
    import_opml_toolbar = "import_opml.toolbar"
    export_opml_toolbar = "export_opml.toolbar"
    subscribe_toolbar = "subscribe.toolbar"
    subscribe_collection_details = "subscribe.collection_details"
    subscribe_collection_suggestions = "subscribe.collection_suggestions"
    refresh_sidebar = "refresh.sidebar"
    search_feeds_discovery_form = "search_feeds.discovery_form"
    add_feed_discovery_results = "add_feed.discovery_results"
    import_opml_form = "import_opml.form"
    show_more_entries_pagination = "show_more.entries_pagination"
    collapse_entries_pagination = "collapse.entries_pagination"
    show_more_tags_pagination = "show_more.tags_pagination"
    collapse_tags_pagination = "collapse.tags_pagination"


class ButtonClicked(BaseEntity):
    name: Literal["button_clicked"]
    view: EventsViewName
    button_type: ButtonType


class TagFilterStateChanged(BaseEntity):
    name: Literal["tag_filter_state_changed"]
    view: EventsViewName
    tag: str
    from_state: Literal["required", "excluded", "none"]
    to_state: Literal["required", "excluded", "none"]
    source: Literal["tags_filter", "entry_record", "rule_record"]


class SidebarStateChanged(BaseEntity):
    name: Literal["sidebar_state_changed"]
    view: EventsViewName
    sub_event: Literal["show", "hide"]
    source: Literal["top_sidebar_button"]


class UserUtm(BaseEntity):
    name: Literal["user_utm"]
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None


Event = Annotated[
    NewsLinkOpened
    | NewsBodyOpened
    | SocialLinkClicked
    | AuthButtonClicked
    | ButtonClicked
    | TagFilterStateChanged
    | SidebarStateChanged
    | UserUtm,
    pydantic.Field(discriminator="name"),
]
