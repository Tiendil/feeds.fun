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

export type CollectionSlug = string & {readonly __brand: unique symbol};

export function toCollectionSlug(slug: string): CollectionSlug {
  return slug as CollectionSlug;
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
  readonly siteUrl: URL | null;
  readonly state: string;
  readonly lastError: string | null;
  readonly loadedAt: Date | null;
  readonly linkedAt: Date | null;
  readonly isOk: boolean;
  readonly collectionIds: CollectionId[];
  readonly young: boolean;
  readonly entriesPerDay: number;
  readonly entriesLoadedDetails: number[] | null;

  constructor({
    id,
    title,
    description,
    url,
    siteUrl,
    state,
    lastError,
    loadedAt,
    linkedAt,
    isOk,
    collectionIds,
    young,
    entriesPerDay,
    entriesLoadedDetails
  }: {
    id: FeedId;
    title: string | null;
    description: string | null;
    url: URL;
    siteUrl: URL | null;
    state: string;
    lastError: string | null;
    loadedAt: Date | null;
    linkedAt: Date | null;
    isOk: boolean;
    collectionIds: CollectionId[];
    young: boolean;
    entriesPerDay: number;
    entriesLoadedDetails: number[] | null;
  }) {
    this.id = id;
    this.title = title;
    this.description = description;
    this.url = url;
    this.siteUrl = siteUrl;
    this.state = state;
    this.lastError = lastError;
    this.loadedAt = loadedAt;
    this.linkedAt = linkedAt;
    this.isOk = isOk;
    this.collectionIds = collectionIds;
    this.young = young;
    this.entriesPerDay = entriesPerDay;
    this.entriesLoadedDetails = entriesLoadedDetails;
  }
}

export type RawFeed = {
  id: string;
  title: string | null;
  description: string | null;
  url: string;
  siteUrl?: string | null;
  state: string;
  lastError?: string | null;
  loadedAt?: string | null;
  linkedAt?: string | null;
  collectionIds: string[];
  young: boolean;
  entriesPerDay: number;
  entriesLoadedDetails?: number[] | null;
};

export function feedFromJSON({
  id,
  title,
  description,
  url,
  siteUrl,
  state,
  lastError,
  loadedAt,
  linkedAt,
  collectionIds,
  young,
  entriesPerDay,
  entriesLoadedDetails
}: RawFeed): Feed {
  return {
    id: toFeedId(id),
    title: title !== null ? title : null,
    description: description !== null ? description : null,
    url: toURL(url),
    siteUrl: siteUrl !== undefined && siteUrl !== null ? toURL(siteUrl) : null,
    state: state,
    lastError: lastError !== undefined ? lastError : null,
    loadedAt: loadedAt !== undefined && loadedAt !== null ? new Date(loadedAt) : null,
    linkedAt: linkedAt !== undefined && linkedAt !== null ? new Date(linkedAt) : null,
    isOk: state === "loaded",
    collectionIds: collectionIds.map(toCollectionId),
    young: young,
    entriesPerDay: entriesPerDay,
    entriesLoadedDetails: entriesLoadedDetails !== undefined ? entriesLoadedDetails : null
  };
}

export type ReferenceExtraValue = number | string | null;

export type RawReference = {
  kind: e.ReferenceKind;
  url: string;
  title?: string | null;
  mime_type?: string | null;
  width?: number | null;
  height?: number | null;
  duration?: string | null;
  size?: number | null;
  extra?: {[key: string]: ReferenceExtraValue} | null;
};

export class Reference {
  readonly kind: e.ReferenceKind;
  readonly url: URL;
  readonly title: string | null;
  readonly mimeType: string | null;
  readonly width: number | null;
  readonly height: number | null;
  readonly duration: string | null;
  readonly size: number | null;
  readonly extra: {[key: string]: ReferenceExtraValue} | null;

  constructor({
    kind,
    url,
    title,
    mimeType,
    width,
    height,
    duration,
    size,
    extra
  }: {
    kind: e.ReferenceKind;
    url: URL;
    title: string | null;
    mimeType: string | null;
    width: number | null;
    height: number | null;
    duration: string | null;
    size: number | null;
    extra: {[key: string]: ReferenceExtraValue} | null;
  }) {
    this.kind = kind;
    this.url = url;
    this.title = title;
    this.mimeType = mimeType;
    this.width = width;
    this.height = height;
    this.duration = duration;
    this.size = size;
    this.extra = extra;
  }

  youtubeId(): string | null {
    const youtubeId = this.extra?.youtube_id;

    return typeof youtubeId === "string" && youtubeId.length > 0 ? youtubeId : null;
  }
}

export function referenceFromJSON({
  kind,
  url,
  title,
  mime_type,
  width,
  height,
  duration,
  size,
  extra
}: RawReference): Reference {
  return new Reference({
    kind: kind,
    url: toURL(url),
    title: title !== undefined ? title : null,
    mimeType: mime_type !== undefined ? mime_type : null,
    width: width !== undefined ? width : null,
    height: height !== undefined ? height : null,
    duration: duration !== undefined ? duration : null,
    size: size !== undefined ? size : null,
    extra: extra !== undefined ? extra : null
  });
}

export class Entry {
  readonly id: EntryId;
  readonly feedId: FeedId;
  readonly title: string;
  readonly url: URL;
  tags: string[];
  readonly markers: e.Marker[];
  readonly score: number;
  readonly scoreContributions: {[key: string]: number};
  readonly scoreToZero: number;
  readonly publishedAt: Date;
  body: string | null;
  references: Reference[] | null;

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
    body,
    references
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
    body: string | null;
    references: Reference[] | null;
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
    this.body = body;
    this.references = references;

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

  hasTags(): boolean {
    return this.tags.length > 0;
  }
}

export type RawEntry = {
  id: string;
  feedId: string;
  title: string;
  url: string;
  tags: number[];
  markers: number[];
  score: number;
  scoreContributions: {[key: number]: number};
  publishedAt: string;
  body?: string | null;
  references?: RawReference[] | null;
};

export function entryFromJSON(rawEntry: RawEntry, tagsMapping: {[key: number]: string}): Entry {
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
    markers: rawEntry.markers.map((m: number) => {
      if (m in e.reverseMarker) {
        return e.reverseMarker[m];
      }

      throw new Error(`Unknown marker: ${m}`);
    }),
    score: rawEntry.score,
    // map keys from int to string
    scoreContributions: contributions,
    publishedAt: new Date(rawEntry.publishedAt),
    body: rawEntry.body !== undefined ? rawEntry.body : null,
    references:
      rawEntry.references !== undefined && rawEntry.references !== null
        ? rawEntry.references.map(referenceFromJSON)
        : null
  });
}

export type Rule = {
  readonly id: RuleId;
  readonly requiredTags: string[];
  readonly excludedTags: string[];
  readonly tags: string[];
  readonly score: number;
  readonly createdAt: Date;
  readonly updatedAt: Date;
};

export function ruleFromJSON({
  id,
  requiredTags,
  excludedTags,
  score,
  createdAt,
  updatedAt
}: {
  id: string;
  requiredTags: string[];
  excludedTags: string[];
  score: number;
  createdAt: string;
  updatedAt: string;
}): Rule {
  requiredTags = requiredTags.sort();
  excludedTags = excludedTags.sort();

  return {
    id: toRuleId(id),
    requiredTags: requiredTags,
    excludedTags: excludedTags,
    tags: requiredTags.concat(excludedTags).sort(),
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

export type RawEntryInfo = {
  title: string;
  body: string;
  url: string;
  publishedAt: string;
};

export function entryInfoFromJSON({title, body, url, publishedAt}: RawEntryInfo): EntryInfo {
  return {title, body, url: toURL(url), publishedAt: new Date(publishedAt)};
}

export type FeedInfo = {
  readonly url: URL;
  readonly siteUrl: URL | null;
  readonly title: string;
  readonly description: string;
  readonly entries: EntryInfo[];
  readonly isLinked: boolean;
};

export type RawFeedInfo = {
  url: string;
  siteUrl?: string | null;
  title: string;
  description: string;
  entries: RawEntryInfo[];
  isLinked: boolean;
};

export function feedInfoFromJSON({url, siteUrl, title, description, entries, isLinked}: RawFeedInfo): FeedInfo {
  return {
    url: toURL(url),
    siteUrl: siteUrl !== undefined && siteUrl !== null ? toURL(siteUrl) : null,
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

export function fakeTag({uid, name, link, categories}: TagInfo): TagInfo {
  return {uid, name, link, categories};
}

export type UserSettingsValue = string | number | boolean;

export type UserSetting = {
  readonly kind: string;
  readonly type: string;
  value: UserSettingsValue;
  readonly name: string;
};

export function userSettingFromJSON({
  kind,
  type,
  value,
  name
}: {
  kind: string;
  type: string;
  value: string | number | boolean;
  name: string;
}): UserSetting {
  return {
    kind,
    type,
    value: type === "decimal" ? parseFloat(value as string) : value,
    name
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
  readonly slug: CollectionSlug;
  readonly guiOrder: number;
  readonly name: string;
  readonly description: string;
  readonly feedsNumber: number;
  readonly showOnMain: boolean;

  constructor({
    id,
    slug,
    guiOrder,
    name,
    description,
    feedsNumber,
    showOnMain
  }: {
    id: CollectionId;
    slug: CollectionSlug;
    guiOrder: number;
    name: string;
    description: string;
    feedsNumber: number;
    showOnMain: boolean;
  }) {
    this.id = id;
    this.slug = slug;
    this.guiOrder = guiOrder;
    this.name = name;
    this.description = description;
    this.feedsNumber = feedsNumber;
    this.showOnMain = showOnMain;
  }
}

export function collectionFromJSON({
  id,
  slug,
  guiOrder,
  name,
  description,
  feedsNumber,
  showOnMain
}: {
  id: string;
  slug: string;
  guiOrder: number;
  name: string;
  description: string;
  feedsNumber: number;
  showOnMain: boolean;
}): Collection {
  return {
    id: toCollectionId(id),
    slug: toCollectionSlug(slug),
    guiOrder: guiOrder,
    name: name,
    description: description,
    feedsNumber: feedsNumber,
    showOnMain: showOnMain
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

export class IntegrationInfo {
  readonly name: string;
  readonly discovery: boolean;
  readonly postprocessing: boolean;

  constructor({name, discovery, postprocessing}: {name: string; discovery: boolean; postprocessing: boolean}) {
    this.name = name;
    this.discovery = discovery;
    this.postprocessing = postprocessing;
  }
}

export type RawIntegrationInfo = {
  name: string;
  discovery: boolean;
  postprocessing: boolean;
};

export function integrationInfoFromJSON({name, discovery, postprocessing}: RawIntegrationInfo): IntegrationInfo {
  return new IntegrationInfo({
    name: name,
    discovery: discovery,
    postprocessing: postprocessing
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

export class stateInfo {
  readonly version: string;
  readonly singleUserMode: boolean;

  constructor({version, singleUserMode}: {version: string; singleUserMode: boolean}) {
    this.version = version;
    this.singleUserMode = singleUserMode;
  }
}

export function stateInfoFromJSON({version, singleUserMode}: {version: string; singleUserMode: boolean}): stateInfo {
  return new stateInfo({version, singleUserMode});
}

export class userInfo {
  readonly userId: string;

  constructor({userId}: {userId: string}) {
    this.userId = userId;
  }
}

export function userInfoFromJSON({userId}: {userId: string}): userInfo {
  return new userInfo({userId});
}

export class ApiError {
  readonly code: string;
  readonly message: string;

  constructor(code: string, message: string) {
    this.code = code;
    this.message = message;
  }
}
