import * as api from "@/logic/api";
import type * as t from "@/logic/types";
import type {State as TagState} from "@/logic/tagsFilterState";

export type TagChangeSource = "tag_filter" | "entry_record";

export async function newsLinkOpened({entryId}: {entryId: t.EntryId}) {
  await api.trackEvent({name: "news_link_opened", entry_id: entryId});
}

export async function newsBodyOpened({entryId}: {entryId: t.EntryId}) {
  await api.trackEvent({name: "news_body_opened", entry_id: entryId});
}

export async function socialLinkClicked({linkType}: {linkType: string}) {
  await api.trackEvent({name: "social_link_clicked", link_type: linkType});
}

async function _tagFilterUsed({operation, tag, source}: {operation: string; tag: string; source: string}) {
  await api.trackEvent({name: "tag_filter_used", operation: operation, tag: tag, source: source});
}

export async function tagStateChanged({
  tag,
  fromState,
  toState,
  source
}: {
  tag: string;
  fromState: TagState;
  toState: TagState;
  source: TagChangeSource;
}) {
  await api.trackEvent({name: "tag_filter_tag_switched", tag: tag, from_state: fromState, to_state: toState});
}
