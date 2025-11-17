import * as _ from "lodash";
import axios, {AxiosError} from "axios";
import * as t from "@/logic/types";
import type * as e from "@/logic/enums";
import * as settings from "@/logic/settings";
import * as cookieConsent from "@/plugins/CookieConsent";
import {useGlobalState} from "@/stores/globalState";o

///////////////
// API handlers
///////////////

const publicEntryPoint = "/spa/api/public";
const privateEntryPoint = "/spa/api/private";

const apiPublic = axios.create({baseURL: publicEntryPoint, withCredentials: true});
const apiPrivate = axios.create({baseURL: privateEntryPoint, withCredentials: true});

// It is an open question what should we do in case of session expiration:
// - redirect to login page
// - redirect to home page & show notification
// Currently the easiest way to handle it is to always redirect to login page.
export function redirectToLogin(returnTo?: string) {
  if (!returnTo) {
    returnTo = window.location.pathname + window.location.search;
  }
  window.location.assign(`/spa/auth/login?return_to=${encodeURIComponent(returnTo)}`);
}

export function redirectToJoin(returnTo?: string) {
  if (!returnTo) {
    returnTo = window.location.pathname + window.location.search;
  }
  window.location.assign(`/spa/auth/join?return_to=${encodeURIComponent(returnTo)}`);
}

export function logoutRedirect() {
  window.location.assign("/spa/auth/logout");
}

let _refreshingAuth: Promise<void> | null = null;

enum Ffun401Behaviour {
  RedirectToLogin = "redirectToLogin",
  DoNotRetry = "doNotRetry",
  ReturnNull = "returnNull"
}

// We try to refresh auth on 401 responses for private API.
// For the public API we do nothing, because it most likely means infrastructure issue.
apiPrivate.interceptors.response.use(
  (r) => r,
  async (error) => {
    const {config, response} = error;

    if (!response) {
      throw error;
    }

    if (response.status !== 401) {
      throw error;
    }

    if (config?.ffunRequestRetried) {
      throw error;
    }

    if (config?.ffun401Behaviour === Ffun401Behaviour.RedirectToLogin) {
      redirectToLogin();
      return; // never reached
    }

    if (config?.ffun401Behaviour === Ffun401Behaviour.DoNotRetry) {
      throw error;
    }

    if (config?.ffun401Behaviour === Ffun401Behaviour.ReturnNull) {
      return {data: null};
    }

    (config as any).ffunRequestRetried = true;

    if (!_refreshingAuth) {
      _refreshingAuth = apiPrivate
        // @ts-ignore
        .post("/refresh-auth", undefined, {ffun401Behaviour: Ffun401Behaviour.RedirectToLogin})
        .then(() => {})
        .finally(() => {
          _refreshingAuth = null;
        });
    }

    await _refreshingAuth; // all 401s await the same refresh

    return apiPrivate(config); // retry the original request generically
  }
);

async function postPublic({url, data}: {url: string; data: any}) {
  const response = await apiPublic.post(url, data);
  return response.data;
}

async function postPrivate({url, data, config}: {url: string; data: any; config?: any}) {
  const response = await apiPrivate.post(url, data, config);
  return response.data;
}

/////////////
// Public API
/////////////

export async function getLastCollectionEntries({
  period,
  collectionSlug,
  minTagCount
}: {
  period: number;
  collectionSlug: t.CollectionSlug | null;
  minTagCount: number;
}) {
  const response = await postPublic({
    url: "/get-last-collection-entries",
    data: {period: period, collectionSlug: collectionSlug, minTagCount: minTagCount}
  });

  const entries = [];

  for (let rawEntry of response.entries) {
    const entry = t.entryFromJSON(rawEntry, response.data.tagsMapping);
    entries.push(entry);
  }

  return entries;
}

export async function getEntriesByIds({ids}: {ids: t.EntryId[]}) {
  const globalState = useGlobalState();

  let response = null;

  if (globalState.loginConfirmed) {
    response = await postPrivate({
      url: "/get-entries-by-ids",
      data: {ids: ids},
      config: {ffun401Behaviour: Ffun401Behaviour.ReturnNull}
    });
  }

  if (!response) {
    response = await postPublic({
      url: "/get-entries-by-ids",
      data: {ids: ids}
    });
  }

  const entries = [];

  for (let rawEntry of response.entries) {
    const entry = t.entryFromJSON(rawEntry, response.tagsMapping);
    entries.push(entry);
  }

  return entries;
}

export async function getCollections() {
  const response = await postPublic({url: "/get-collections", data: {}});

  const collections = [];

  for (let rawCollection of response.collections) {
    const collection = t.collectionFromJSON(rawCollection);
    collections.push(collection);
  }

  return collections;
}

export async function getCollectionFeeds({collectionId}: {collectionId: t.CollectionId}) {
  const response = await postPublic({
    url: "/get-collection-feeds",
    data: {collectionId: collectionId}
  });

  const feeds = [];

  for (let rawFeed of response.feeds) {
    const feed = t.collectionFeedInfoFromJSON(rawFeed);
    feeds.push(feed);
  }

  return feeds;
}

export async function getTagsInfo({uids}: {uids: string[]}) {
  const response = await postPublic({url: "/get-tags-info", data: {uids: uids}});

  const tags: {[key: string]: t.TagInfo} = {};

  for (let uid in response.tags) {
    const rawTag = response.tags[uid];
    const tag = t.tagInfoFromJSON(rawTag);
    tags[uid] = tag;
  }

  return tags;
}

export async function getInfo() {
  const response = await postPublic({url: "/get-info", data: {}});

  return t.stateInfoFromJSON(response);
}

export async function getUser() {
  const response = await postPrivate({url: "/get-user", data: {}, config: {ffun401Behaviour: Ffun401Behaviour.ReturnNull}});

  if (!response) {
    return null;
  }

  return t.userInfoFromJSON(response);
}

export function trackEvent(authenticated: bool, data: {[key: string]: string | number | null}) {
  if (!settings.trackEvents) {
    return;
  }

  if (!cookieConsent.isAnalyticsAllowed()) {
    return;
  }

  let url: string;

  if (authenticated) {
    url = privateEntryPoint + "/track-event";
  }
  else {
    url = publicEntryPoint + "/track-event";
  }

  let payload = JSON.stringify({event: data});

  if ("sendBeacon" in navigator) {
    return navigator.sendBeacon(url, payload);
  }

  // Fallback: fire-and-forget; avoid preflight by using text/plain + no-cors
  fetch(url, {
    method: "POST",
    keepalive: true,
    mode: "no-cors",
    headers: {"Content-Type": "text/plain;charset=UTF-8"},
    body: payload
  }).catch(() => {});
}

//////////////
// Private API
//////////////

export async function getFeeds() {
  const response = await postPrivate({url: "/get-feeds", data: {}});

  const feeds = [];

  for (let rawFeed of response.feeds) {
    const feed = t.feedFromJSON(rawFeed);
    feeds.push(feed);
  }

  return feeds;
}

export async function getLastEntries({period, minTagCount}: {period: number; minTagCount: number}) {
  const response = await postPrivate({
    url: "/get-last-entries",
    data: {
      period: period,
      minTagCount: minTagCount
    }
  });

  const entries = [];

  for (let rawEntry of response.entries) {
    const entry = t.entryFromJSON(rawEntry, response.tagsMapping);
    entries.push(entry);
  }

  return entries;
}

export async function createOrUpdateRule({
  requiredTags,
  excludedTags,
  score
}: {
  requiredTags: string[];
  excludedTags: string[];
  score: number;
}) {
  const response = await postPrivate({
    url: "/create-or-update-rule",
    data: {
      requiredTags: requiredTags,
      excludedTags: excludedTags,
      score: score
    }
  });
  return response;
}

export async function deleteRule({id}: {id: t.RuleId}) {
  const response = await postPrivate({url: "/delete-rule", data: {id: id}});
  return response;
}

export async function updateRule({
  id,
  requiredTags,
  excludedTags,
  score
}: {
  id: t.RuleId;
  requiredTags: string[];
  excludedTags: string[];
  score: number;
}) {
  const response = await postPrivate({
    url: "/update-rule",
    data: {id: id, score: score, requiredTags: requiredTags, excludedTags: excludedTags}
  });
  return response;
}

export async function getRules() {
  const response = await postPrivate({url: "/get-rules", data: {}});

  const rules = [];

  for (let rawRule of response.rules) {
    const rule = t.ruleFromJSON(rawRule);
    rules.push(rule);
  }

  return rules;
}

export async function getScoreDetails({entryId}: {entryId: t.EntryId}) {
  const response = await postPrivate({
    url: "/get-score-details",
    data: {entryId: entryId}
  });

  const rules = [];

  for (let rawRule of response.rules) {
    const rule = t.ruleFromJSON(rawRule);
    rules.push(rule);
  }

  return rules;
}

export async function setMarker({entryId, marker}: {entryId: t.EntryId; marker: e.Marker}) {
  await postPrivate({
    url: "/set-marker",
    data: {entryId: entryId, marker: marker}
  });
}

export async function removeMarker({entryId, marker}: {entryId: t.EntryId; marker: e.Marker}) {
  await postPrivate({
    url: "/remove-marker",
    data: {entryId: entryId, marker: marker}
  });
}

export async function discoverFeeds({url}: {url: string}) {
  const response = await postPrivate({url: "/discover-feeds", data: {url: url}});

  const feeds = [];
  const messages = [];

  for (let rawFeed of response.feeds) {
    const feed = t.feedInfoFromJSON(rawFeed);
    feeds.push(feed);
  }

  for (let rawMessage of response.messages) {
    const message = t.apiMessageFromJSON(rawMessage);
    messages.push(message);
  }

  return {feeds, messages};
}

export async function addFeed({url}: {url: string}) {
  const response = await postPrivate({url: "/add-feed", data: {url: url}});

  return t.feedFromJSON(response.feed);
}

export async function addOPML({content}: {content: string}) {
  await postPrivate({url: "/add-opml", data: {content: content}});
}

export async function unsubscribe({feedId}: {feedId: t.FeedId}) {
  await postPrivate({url: "/unsubscribe", data: {feedId: feedId}});
}

export async function subscribeToCollections({collectionsIds}: {collectionsIds: t.CollectionId[]}) {
  await postPrivate({
    url: "/subscribe-to-collections",
    data: {collections: collectionsIds}
  });
}

export async function getUserSettings() {
  const response = await postPrivate({url: "/get-user-settings", data: {}});

  const settings: {[key: string]: t.UserSetting} = {};

  for (let rawSetting of response.settings) {
    const setting = t.userSettingFromJSON(rawSetting);
    settings[setting.kind] = setting;
  }

  return settings;
}

export async function setUserSetting({kind, value}: {kind: string; value: string | number | boolean}) {
  await postPrivate({url: "/set-user-setting", data: {kind: kind, value: value}});
}

export async function getResourceHistory({kind}: {kind: string}) {
  const response = await postPrivate({
    url: "/get-resource-history",
    data: {kind: kind}
  });

  const history = [];

  for (let rawRecord of response.history) {
    const record = t.resourceHistoryRecordFromJSON(rawRecord);
    history.push(record);
  }

  return history;
}

export async function removeUser() {
  await postPrivate({url: "/remove-user", data: {}});
}
