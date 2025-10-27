import * as _ from "lodash";
import axios, {AxiosError} from "axios";
import * as t from "@/logic/types";
import type * as e from "@/logic/enums";
import * as settings from "@/logic/settings";
import * as cookieConsent from "@/plugins/CookieConsent";

const ENTRY_POINT_PUBLIC = "/api/spa/public";
const ENTRY_POINT_PRIVATE = "/api/spa/private";

/////////////
// Public API
/////////////

const API_GET_LAST_COLLECTION_ENTRIES = `${ENTRY_POINT_PUBLIC}/get-last-collection-entries`;
const API_GET_ENTRIES_BY_IDS = `${ENTRY_POINT_PUBLIC}/get-entries-by-ids`;
const API_GET_COLLECTIONS = `${ENTRY_POINT_PUBLIC}/get-collections`;
const API_GET_COLLECTION_FEEDS = `${ENTRY_POINT_PUBLIC}/get-collection-feeds`;
const API_GET_TAGS_INFO = `${ENTRY_POINT_PUBLIC}/get-tags-info`;
const API_GET_INFO = `${ENTRY_POINT_PUBLIC}/get-info`;
const API_TRACK_EVENT = `${ENTRY_POINT_PUBLIC}/track-event`;

//////////////
// Private API
//////////////

const API_GET_FEEDS = `${ENTRY_POINT_PRIVATE}/get-feeds`;
const API_GET_LAST_ENTRIES = `${ENTRY_POINT_PRIVATE}/get-last-entries`;
const API_CREATE_OR_UPDATE_RULE = `${ENTRY_POINT_PRIVATE}/create-or-update-rule`;
const API_DELETE_RULE = `${ENTRY_POINT_PRIVATE}/delete-rule`;
const API_UPDATE_RULE = `${ENTRY_POINT_PRIVATE}/update-rule`;
const API_GET_RULES = `${ENTRY_POINT_PRIVATE}/get-rules`;
const API_GET_SCORE_DETAILS = `${ENTRY_POINT_PRIVATE}/get-score-details`;
const API_SET_MARKER = `${ENTRY_POINT_PRIVATE}/set-marker`;
const API_REMOVE_MARKER = `${ENTRY_POINT_PRIVATE}/remove-marker`;
const API_DISCOVER_FEEDS = `${ENTRY_POINT_PRIVATE}/discover-feeds`;
const API_ADD_FEED = `${ENTRY_POINT_PRIVATE}/add-feed`;
const API_ADD_OPML = `${ENTRY_POINT_PRIVATE}/add-opml`;
const API_UNSUBSCRIBE = `${ENTRY_POINT_PRIVATE}/unsubscribe`;
const API_SUBSCRIBE_TO_COLLECTIONS = `${ENTRY_POINT_PRIVATE}/subscribe-to-collections`;
const API_GET_USER_SETTINGS = `${ENTRY_POINT_PRIVATE}/get-user-settings`;
const API_SET_USER_SETTING = `${ENTRY_POINT_PRIVATE}/set-user-setting`;
const API_GET_RESOURCE_HISTORY = `${ENTRY_POINT_PRIVATE}/get-resource-history`;
const API_REMOVE_USER = `${ENTRY_POINT_PRIVATE}/remove-user`;

///////////////
// Common logic
///////////////

let _onSessionLost: () => void = () => {};

export function init({onSessionLost}: {onSessionLost: () => void}) {
  _onSessionLost = onSessionLost;
}

async function post({url, data}: {url: string; data: any}) {
  try {
    const response = await axios.post(url, data);
    return response.data;
  } catch (error) {
    console.log(error);

    if (error instanceof Error && "response" in error) {
      const axiosError = error as AxiosError;
      if (axiosError.response && axiosError.response.status === 401) {
        await _onSessionLost();
      }
    }

    throw error;
  }
}

////////////
// API calls
////////////

export async function getFeeds() {
  const response = await post({url: API_GET_FEEDS, data: {}});

  const feeds = [];

  for (let rawFeed of response.feeds) {
    const feed = t.feedFromJSON(rawFeed);
    feeds.push(feed);
  }

  return feeds;
}

export async function getLastEntries({period, minTagCount}: {period: number; minTagCount: number}) {
  const response = await post({
    url: API_GET_LAST_ENTRIES,
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

export async function getLastCollectionEntries({
  period,
  collectionSlug,
  minTagCount
}: {
  period: number;
  collectionSlug: t.CollectionSlug | null;
  minTagCount: number;
}) {
  const response = await post({
    url: API_GET_LAST_COLLECTION_ENTRIES,
    data: {period: period, collectionSlug: collectionSlug, minTagCount: minTagCount}
  });

  const entries = [];

  for (let rawEntry of response.entries) {
    const entry = t.entryFromJSON(rawEntry, response.tagsMapping);
    entries.push(entry);
  }

  return entries;
}

export async function getEntriesByIds({ids}: {ids: t.EntryId[]}) {
  const response = await post({
    url: API_GET_ENTRIES_BY_IDS,
    data: {ids: ids}
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
  const response = await post({
    url: API_CREATE_OR_UPDATE_RULE,
    data: {
      requiredTags: requiredTags,
      excludedTags: excludedTags,
      score: score
    }
  });
  return response;
}

export async function deleteRule({id}: {id: t.RuleId}) {
  const response = await post({url: API_DELETE_RULE, data: {id: id}});
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
  const response = await post({
    url: API_UPDATE_RULE,
    data: {id: id, score: score, requiredTags: requiredTags, excludedTags: excludedTags}
  });
  return response;
}

export async function getRules() {
  const response = await post({url: API_GET_RULES, data: {}});

  const rules = [];

  for (let rawRule of response.rules) {
    const rule = t.ruleFromJSON(rawRule);
    rules.push(rule);
  }

  return rules;
}

export async function getScoreDetails({entryId}: {entryId: t.EntryId}) {
  const response = await post({
    url: API_GET_SCORE_DETAILS,
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
  await post({
    url: API_SET_MARKER,
    data: {entryId: entryId, marker: marker}
  });
}

export async function removeMarker({entryId, marker}: {entryId: t.EntryId; marker: e.Marker}) {
  await post({
    url: API_REMOVE_MARKER,
    data: {entryId: entryId, marker: marker}
  });
}

export async function discoverFeeds({url}: {url: string}) {
  const response = await post({url: API_DISCOVER_FEEDS, data: {url: url}});

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
  const response = await post({url: API_ADD_FEED, data: {url: url}});

  return t.feedFromJSON(response.feed);
}

export async function addOPML({content}: {content: string}) {
  await post({url: API_ADD_OPML, data: {content: content}});
}

export async function unsubscribe({feedId}: {feedId: t.FeedId}) {
  await post({url: API_UNSUBSCRIBE, data: {feedId: feedId}});
}

export async function getCollections() {
  const response = await post({url: API_GET_COLLECTIONS, data: {}});

  const collections = [];

  for (let rawCollection of response.collections) {
    const collection = t.collectionFromJSON(rawCollection);
    collections.push(collection);
  }

  return collections;
}

export async function getCollectionFeeds({collectionId}: {collectionId: t.CollectionId}) {
  const response = await post({
    url: API_GET_COLLECTION_FEEDS,
    data: {collectionId: collectionId}
  });

  const feeds = [];

  for (let rawFeed of response.feeds) {
    const feed = t.collectionFeedInfoFromJSON(rawFeed);
    feeds.push(feed);
  }

  return feeds;
}

export async function subscribeToCollections({collectionsIds}: {collectionsIds: t.CollectionId[]}) {
  await post({
    url: API_SUBSCRIBE_TO_COLLECTIONS,
    data: {collections: collectionsIds}
  });
}

export async function getTagsInfo({uids}: {uids: string[]}) {
  const response = await post({url: API_GET_TAGS_INFO, data: {uids: uids}});

  const tags: {[key: string]: t.TagInfo} = {};

  for (let uid in response.tags) {
    const rawTag = response.tags[uid];
    const tag = t.tagInfoFromJSON(rawTag);
    tags[uid] = tag;
  }

  return tags;
}

export async function getUserSettings() {
  const response = await post({url: API_GET_USER_SETTINGS, data: {}});

  const settings: {[key: string]: t.UserSetting} = {};

  for (let rawSetting of response.settings) {
    const setting = t.userSettingFromJSON(rawSetting);
    settings[setting.kind] = setting;
  }

  return settings;
}

export async function setUserSetting({kind, value}: {kind: string; value: string | number | boolean}) {
  await post({url: API_SET_USER_SETTING, data: {kind: kind, value: value}});
}

export async function getResourceHistory({kind}: {kind: string}) {
  const response = await post({
    url: API_GET_RESOURCE_HISTORY,
    data: {kind: kind}
  });

  const history = [];

  for (let rawRecord of response.history) {
    const record = t.resourceHistoryRecordFromJSON(rawRecord);
    history.push(record);
  }

  return history;
}

export async function getInfo() {
  const response = await post({url: API_GET_INFO, data: {}});

  return response;
}

export async function trackEvent(data: {[key: string]: string | number | null}) {
  if (!settings.trackEvents) {
    return;
  }

  if (!cookieConsent.isAnalyticsAllowed()) {
    return;
  }

  await post({url: API_TRACK_EVENT, data: {event: data}});
}

export async function removeUser() {
  await post({url: API_REMOVE_USER, data: {}});
}
