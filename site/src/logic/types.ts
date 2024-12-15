import * as e from "@/logic/enums";

export type FeedId = string & {readonly __brand: unique symbol};

export function toFeedId(id: string): FeedId {
  return id as FeedId;
}

export type EntryId = string & {readonly __brand: unique symbol};

export function toEntryId(id: string): EntryId {
  return id as EntryId;
}

export type RuleId = string & {readonly __brand: unique symbol};

export function toRuleId(id: string): RuleId {
  return id as RuleId;
}

export type CollectionId = string & {readonly __brand: unique symbol};

export function toCollectionId(id: string): CollectionId {
  return id as CollectionId;
}

export type URL = string & {readonly __brand: unique symbol};

export function toURL(url: string): URL {
  return url as URL;
}

export class Feed {
  readonly id: FeedId;
  readonly title: string | null;
  readonly description: string | null;
  readonly url: URL;
  readonly state: string;
  readonly lastError: string | null;
  readonly loadedAt: Date | null;
  readonly linkedAt: Date;
  readonly isOk: boolean;
  readonly collectionIds: CollectionId[];

  constructor({
    id,
    title,
    description,
    url,
    state,
    lastError,
    loadedAt,
    linkedAt,
    isOk,
    collectionIds
  }: {
    id: FeedId;
    title: string | null;
    description: string | null;
    url: URL;
    state: string;
    lastError: string | null;
    loadedAt: Date | null;
    linkedAt: Date;
    isOk: boolean;
    collectionIds: CollectionId[];
  }) {
    this.id = id;
    this.title = title;
    this.description = description;
    this.url = url;
    this.state = state;
    this.lastError = lastError;
    this.loadedAt = loadedAt;
    this.linkedAt = linkedAt;
    this.isOk = isOk;
    this.collectionIds = collectionIds;
  }
}

export function feedFromJSON({
  id,
  title,
  description,
  url,
  state,
  lastError,
  loadedAt,
  linkedAt,
  collectionIds
}: {
  id: string;
  title: string;
  description: string;
  url: string;
  state: string;
  lastError: string | null;
  loadedAt: string;
  linkedAt: string;
  collectionIds: string[];
}): Feed {
  return {
    id: toFeedId(id),
    title: title !== null ? title : null,
    description: description !== null ? description : null,
    url: toURL(url),
    state: state,
    lastError: lastError,
    loadedAt: loadedAt !== null ? new Date(loadedAt) : null,
    linkedAt: new Date(linkedAt),
    isOk: state === "loaded",
    collectionIds: collectionIds.map(toCollectionId)
  };
}

export class Entry {
  readonly id: EntryId;
  readonly feedId: FeedId;
  readonly title: string;
  readonly url: URL;
  readonly tags: string[];
  readonly markers: e.Marker[];
  readonly score: number;
  readonly scoreContributions: {[key: string]: number};
  readonly scoreToZero: number;
  readonly publishedAt: Date;
  readonly catalogedAt: Date;
  body: string | null;

  constructor({
    id,
    feedId,
    title,
    url,
    tags,
    markers,
    score,
    scoreContributions,
    publishedAt,
    catalogedAt,
    body
  }: {
    id: EntryId;
    feedId: FeedId;
    title: string;
    url: URL;
    tags: string[];
    markers: e.Marker[];
    score: number;
    scoreContributions: {[key: string]: number};
    publishedAt: Date;
    catalogedAt: Date;
    body: string | null;
  }) {
    this.id = id;
    this.feedId = feedId;
    this.title = title;
    this.url = url;
    this.tags = tags;
    this.markers = markers;
    this.score = score;
    this.scoreContributions = scoreContributions;
    this.publishedAt = publishedAt;
    this.catalogedAt = catalogedAt;
    this.body = body;

    this.scoreToZero = -Math.abs(score);
  }

  setMarker(marker: e.Marker): void {
    if (!this.hasMarker(marker)) {
      this.markers.push(marker);
    }
  }

  removeMarker(marker: e.Marker): void {
    if (this.hasMarker(marker)) {
      this.markers.splice(this.markers.indexOf(marker), 1);
    }
  }

  hasMarker(marker: e.Marker): boolean {
    return this.markers.includes(marker);
  }
}

export function entryFromJSON(
  rawEntry: {
    id: string;
    feedId: string;
    title: string;
    url: string;
    tags: number[];
    markers: string[];
    score: number;
    scoreContributions: {[key: number]: number};
    publishedAt: string;
    catalogedAt: string;
    body: string | null;
  },
  tagsMapping: {[key: number]: string}
): Entry {
  const contributions: {[key: string]: number} = {};

  for (const key in rawEntry.scoreContributions) {
    contributions[tagsMapping[key]] = rawEntry.scoreContributions[key];
  }

  return new Entry({
    id: toEntryId(rawEntry.id),
    feedId: toFeedId(rawEntry.feedId),
    title: rawEntry.title,
    url: toURL(rawEntry.url),
    tags: rawEntry.tags.map((t: number) => tagsMapping[t]),
    markers: rawEntry.markers.map((m: string) => {
      if (m in e.reverseMarker) {
        return e.reverseMarker[m];
      }

      throw new Error(`Unknown marker: ${m}`);
    }),
    score: rawEntry.score,
    // map keys from int to string
    scoreContributions: contributions,
    publishedAt: new Date(rawEntry.publishedAt),
    catalogedAt: new Date(rawEntry.catalogedAt),

    body: rawEntry.body
  });
}

export type Rule = {
  readonly id: RuleId;
  readonly tags: string[];
  readonly score: number;
  readonly createdAt: Date;
  readonly updatedAt: Date;
};

export function ruleFromJSON({
  id,
  tags,
  score,
  createdAt,
  updatedAt
}: {
  id: string;
  tags: string[];
  score: number;
  createdAt: string;
  updatedAt: string;
}): Rule {
  tags = tags.sort();

  return {
    id: toRuleId(id),
    tags: tags,
    score: score,
    createdAt: new Date(createdAt),
    updatedAt: new Date(updatedAt)
  };
}

export type EntryInfo = {
  readonly title: string;
  readonly body: string;
  readonly url: URL;
  readonly publishedAt: Date;
};

export function entryInfoFromJSON({
  title,
  body,
  url,
  publishedAt
}: {
  title: string;
  body: string;
  url: string;
  publishedAt: string;
}): EntryInfo {
  return {title, body, url: toURL(url), publishedAt: new Date(publishedAt)};
}

export type FeedInfo = {
  readonly url: URL;
  readonly title: string;
  readonly description: string;
  readonly entries: EntryInfo[];
  readonly isLinked: boolean;
};

export function feedInfoFromJSON({
  url,
  title,
  description,
  entries,
  isLinked
}: {
  url: string;
  title: string;
  description: string;
  entries: any[];
  isLinked: boolean;
}): FeedInfo {
  return {
    url: toURL(url),
    title,
    description,
    entries: entries.map(entryInfoFromJSON),
    isLinked
  };
}

export type TagInfo = {
  readonly uid: string;
  readonly name: string | null;
  readonly link: string | null;
  readonly categories: string[];
};

export function tagInfoFromJSON({
  uid,
  name,
  link,
  categories
}: {
  uid: string;
  name: string | null;
  link: string | null;
  categories: string[];
}): TagInfo {
  return {uid, name: name, link: link, categories};
}

export function noInfoTag(uid: string): TagInfo {
  return {uid, name: uid, link: null, categories: []};
}

export type UserSetting = {
  readonly kind: string;
  readonly type: string;
  value: string | number | boolean;
  readonly name: string;
  readonly description: string;
};

export function userSettingFromJSON({
  kind,
  type,
  value,
  name,
  description
}: {
  kind: string;
  type: string;
  value: string | number | boolean;
  name: string;
  description: string;
}): UserSetting {
  return {
    kind,
    type,
    value: type === "decimal" ? parseFloat(value as string) : value,
    name,
    description
  };
}

export class ResourceHistoryRecord {
  readonly intervalStartedAt: Date;
  readonly used: number;
  readonly reserved: number;

  constructor({intervalStartedAt, used, reserved}: {intervalStartedAt: Date; used: number; reserved: number}) {
    this.intervalStartedAt = intervalStartedAt;
    this.used = used;
    this.reserved = reserved;
  }

  total(): number {
    return this.used + this.reserved;
  }
}

export function resourceHistoryRecordFromJSON({
  intervalStartedAt,
  used,
  reserved
}: {
  intervalStartedAt: string;
  used: number | string;
  reserved: number | string;
}): ResourceHistoryRecord {
  return new ResourceHistoryRecord({
    intervalStartedAt: new Date(intervalStartedAt),
    // TODO: refactor to use kind of Decimals and to respect input types
    used: parseFloat(used as string),
    reserved: parseFloat(reserved as string)
  });
}

export class Collection {
  readonly id: CollectionId;
  readonly guiOrder: number;
  readonly name: string;
  readonly description: string;
  readonly feedsNumber: number;

  constructor({
    id,
    guiOrder,
    name,
    description,
    feedsNumber
  }: {
    id: CollectionId;
    guiOrder: number;
    name: string;
    description: string;
    feedsNumber: number;
  }) {
    this.id = id;
    this.guiOrder = guiOrder;
    this.name = name;
    this.description = description;
    this.feedsNumber = feedsNumber;
  }
}

export function collectionFromJSON({
  id,
  guiOrder,
  name,
  description,
  feedsNumber
}: {
  id: string;
  guiOrder: number;
  name: string;
  description: string;
  feedsNumber: number;
}): Collection {
  return {
    id: toCollectionId(id),
    guiOrder: guiOrder,
    name: name,
    description: description,
    feedsNumber: feedsNumber
  };
}

export class CollectionFeedInfo {
  readonly url: URL;
  readonly title: string;
  readonly description: string;
  readonly id: FeedId;

  constructor({url, title, description, id}: {url: URL; title: string; description: string; id: FeedId}) {
    this.url = url;
    this.title = title;
    this.description = description;
    this.id = id;
  }
}

export function collectionFeedInfoFromJSON({
  url,
  title,
  description,
  id
}: {
  url: string;
  title: string;
  description: string;
  id: string;
}): CollectionFeedInfo {
  return new CollectionFeedInfo({
    url: toURL(url),
    title: title,
    description: description,
    id: toFeedId(id)
  });
}

export class ApiMessage {
  readonly type: string;
  readonly code: string;
  readonly message: string;

  constructor({type, code, message}: {type: string; code: string; message: string}) {
    this.type = type;
    this.code = code;
    this.message = message;
  }
}

export function apiMessageFromJSON({type, code, message}: {type: string; code: string; message: string}): ApiMessage {
  return new ApiMessage({type, code, message});
}
