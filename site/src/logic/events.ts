
import * as api from "@/logic/api";
import * as t from "@/logic/types";


export async function newsLinkOpened({entryId}: {entryId: t.EntryId}) {
  await api.trackEvent({name: "news_link_opened", entry_id: entryId});
}


export async function newsBodyOpened({entryId}: {entryId: t.EntryId}) {
  await api.trackEvent({name: "news_body_opened", entry_id: entryId});
}
