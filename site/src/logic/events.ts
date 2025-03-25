import * as api from "@/logic/api";
import type * as t from "@/logic/types";
import type {State as TagState} from "@/logic/tagsFilterState";

export type TagChangeSource = ("news_tags_filter" | "rules_tags_filter" | "public_collections_tags_filter" |
                               "entry_record" | "rule_record");

export async function newsLinkOpened({entryId}: {entryId: t.EntryId}) {
  await api.trackEvent({name: "news_link_opened", entry_id: entryId});
}

export async function newsBodyOpened({entryId}: {entryId: t.EntryId}) {
  await api.trackEvent({name: "news_body_opened", entry_id: entryId});
}

export async function socialLinkClicked({linkType}: {linkType: string}) {
  await api.trackEvent({name: "social_link_clicked", link_type: linkType});
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
  await api.trackEvent({
    name: "tag_filter_state_changed",
    tag: tag,
    from_state: fromState,
    to_state: toState,
    source: source
  });
}
