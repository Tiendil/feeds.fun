import * as api from "@/logic/api";
import type * as t from "@/logic/types";
import {inject} from "vue";
import type {State as TagState} from "@/logic/tagsFilterState";
import * as asserts from "@/logic/asserts";

export type EventsViewName =
  | "news"
  | "rules"
  | "public_collections"
  | "auth"
  | "settings"
  | "discovery"
  | "feeds"
  | "main"
  | "collections";
export type TagChangeSource = "tags_filter" | "entry_record" | "rule_record";

export type SidebarVisibilityChangeEvent = "hide" | "show";
export type SidebarVisibilityChangeSource = "top_sidebar_button";

export type AuthButtonType = "login" | "join" | "go_to_feeds" | "register.toolbar" | "register.tags_filter";
export type ButtonType =
  | "add_feed.toolbar"
  | "import_opml.toolbar"
  | "export_opml.toolbar"
  | "subscribe.toolbar"
  | "subscribe.collection_details"
  | "subscribe.collection_suggestions"
  | "refresh.sidebar"
  | "search_feeds.discovery_form"
  | "add_feed.discovery_results"
  | "import_opml.form"
  | `show_more.${string}`
  | `collapse.${string}`;

export type ClickEventProps = {
  clickEventName?: "button_clicked" | "auth_button_clicked";
  clickEventButtonType?: ButtonType | AuthButtonType;
};

export function useEventsView(): EventsViewName {
  const view = inject<EventsViewName>("eventsViewName");
  asserts.defined(view, "eventsViewName");
  return view;
}

export function useButtonClickTracking(properties: ClickEventProps, onClick: (event: MouseEvent) => void) {
  const view = inject<EventsViewName | undefined>("eventsViewName", undefined);

  return (event: MouseEvent) => {
    if (properties.clickEventButtonType !== undefined) {
      asserts.defined(view, "eventsViewName");
      api.trackEvent({
        name: properties.clickEventName ?? "button_clicked",
        view,
        button_type: properties.clickEventButtonType
      });
    }

    onClick(event);
  };
}

export function newsLinkOpened({entryId, view}: {entryId: t.EntryId; view: EventsViewName}) {
  api.trackEvent({
    name: "news_link_opened",
    view: view,
    entry_id: entryId
  });
}

export function newsBodyOpened({entryId, view}: {entryId: t.EntryId; view: EventsViewName}) {
  api.trackEvent({
    name: "news_body_opened",
    view: view,
    entry_id: entryId
  });
}

export function socialLinkClicked({linkType, view}: {linkType: string; view: EventsViewName}) {
  api.trackEvent({
    name: "social_link_clicked",
    view: view,
    link_type: linkType
  });
}

export function authButtonClicked({buttonType, view}: {buttonType: AuthButtonType; view: EventsViewName}) {
  api.trackEvent({
    name: "auth_button_clicked",
    view: view,
    button_type: buttonType
  });
}

export function buttonClicked({buttonType, view}: {buttonType: ButtonType; view: EventsViewName}) {
  api.trackEvent({
    name: "button_clicked",
    view: view,
    button_type: buttonType
  });
}

export function sidebarStateChanged({
  subEvent,
  view,
  source
}: {
  subEvent: SidebarVisibilityChangeEvent;
  view: EventsViewName;
  source: SidebarVisibilityChangeSource;
}) {
  api.trackEvent({
    name: "sidebar_state_changed",
    view: view,
    sub_event: subEvent,
    source: source
  });
}

export function tagStateChanged({
  tag,
  fromState,
  toState,
  source,
  view
}: {
  tag: string;
  fromState: TagState;
  toState: TagState;
  source: TagChangeSource;
  view: EventsViewName;
}) {
  // const eventsView = inject<events.EventViewName>("eventsViewName");

  api.trackEvent({
    name: "tag_filter_state_changed",
    tag: tag,
    from_state: fromState,
    to_state: toState,
    view: view,
    source: source
  });
}

export function trackUtm({
  utm_source,
  utm_medium,
  utm_campaign
}: {
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
}) {
  api.trackEvent({
    name: "user_utm",
    utm_source: utm_source,
    utm_medium: utm_medium,
    utm_campaign: utm_campaign
  });
}
