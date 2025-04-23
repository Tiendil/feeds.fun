import * as api from "@/logic/api";
import type * as t from "@/logic/types";
import {inject} from "vue";
import type {State as TagState} from "@/logic/tagsFilterState";

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

export async function newsLinkOpened({entryId, view}: {entryId: t.EntryId; view: EventsViewName}) {
  await api.trackEvent({
    name: "news_link_opened",
    view: view,
    entry_id: entryId
  });
}

export async function newsBodyOpened({entryId, view}: {entryId: t.EntryId; view: EventsViewName}) {
  await api.trackEvent({
    name: "news_body_opened",
    view: view,
    entry_id: entryId
  });
}

export async function socialLinkClicked({linkType, view}: {linkType: string; view: EventsViewName}) {
  await api.trackEvent({
    name: "social_link_clicked",
    view: view,
    link_type: linkType
  });
}

export async function sidebarStateChanged({
  subEvent,
  view,
  source
}: {
  subEvent: SidebarVisibilityChangeEvent;
  view: EventsViewName;
  source: SidebarVisibilityChangeSource;
}) {
  await api.trackEvent({
    name: "sidebar_state_changed",
    view: view,
    sub_event: subEvent,
    source: source
  });
}

export async function tagStateChanged({
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

  await api.trackEvent({
    name: "tag_filter_state_changed",
    tag: tag,
    from_state: fromState,
    to_state: toState,
    view: view,
    source: source
  });
}

export async function trackUtm({
  utm_source,
  utm_medium,
  utm_campaign
}: {
  utm_source: string;
  utm_medium: string;
  utm_campaign: string;
}) {
  await api.trackEvent({
    name: "user_utm",
    utm_source: utm_source,
    utm_medium: utm_medium,
    utm_campaign: utm_campaign
  });
}
