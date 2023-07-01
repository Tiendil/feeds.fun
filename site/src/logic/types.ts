import * as e from "@/logic/enums";


export type FeedId = string & { readonly __brand: unique symbol };

export function toFeedId(id: string): FeedId {
    return id as FeedId;
}


export type EntryId = string & { readonly __brand: unique symbol };

export function toEntryId(id: string): EntryId {
    return id as EntryId;
}


export type RuleId = string & { readonly __brand: unique symbol };

export function toRuleId(id: string): RuleId {
    return id as RuleId;
}

export type URL = string & { readonly __brand: unique symbol };

export function toURL(url: string): URL {
    return url as URL;
}

export type Feed = {
    readonly id: FeedId;
    readonly title: string|null;
    readonly description: string|null;
    readonly url: URL;
    readonly state: string;
    readonly lastError: string|null;
    readonly loadedAt: Date|null;
};


export function feedFromJSON({ id, title, description, url, state, lastError, loadedAt }:
                             { id: string, title: string, description: string, url: string,
                               state: string, lastError: string|null, loadedAt: string }): Feed {
    return { id: toFeedId(id),
             title: title !== null ? title : null,
             description: description !== null ? description : null,
             url: toURL(url),
             state: state,
             lastError: lastError,
             loadedAt: loadedAt !== null ? new Date(loadedAt) : null };
}


export class Entry {
    readonly id: EntryId;
    readonly feedId: FeedId;
    readonly title: string;
    readonly url: URL;
    readonly tags: string[];
    readonly markers: e.Marker[];
    readonly score: number;
    readonly scoreToZero: number;
    readonly publishedAt: Date;
    readonly catalogedAt: Date;
    body: string|null;

    constructor({ id, feedId, title, url, tags, markers, score, publishedAt, catalogedAt, body }:
                { id: EntryId, feedId: FeedId, title: string, url: URL, tags: string[],
                  markers: e.Marker[], score: number,
                  publishedAt: Date, catalogedAt: Date, body: string|null }) {
        this.id = id;
        this.feedId = feedId;
        this.title = title;
        this.url = url;
        this.tags = tags;
        this.markers = markers;
        this.score = score;
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


export function entryFromJSON({ id, feedId, title, url, tags, markers, score, publishedAt, catalogedAt, body }:
                              { id: string, feedId: string, title: string, url: string, tags: string[],
                                markers: string[], score: number,
                                publishedAt: string, catalogedAt: string, body: string|null }): Entry {
    return new Entry({ id: toEntryId(id),
                       feedId: toFeedId(feedId),
                       title,
                       url: toURL(url),
                       tags: tags,
                       markers: markers.map(m => e.reverseMarker[m]),
                       score: score,
                       publishedAt: new Date(publishedAt),
                       catalogedAt: new Date(catalogedAt),
                       body: body });
}


export type Rule = {
    readonly id: RuleId;
    readonly tags: string[];
    readonly score: number;
    readonly createdAt: Date;
}


export function ruleFromJSON({ id, tags, score, createdAt }:
                             { id: string, tags: string[], score: number, createdAt: string }): Rule {
    return { id: toRuleId(id),
             tags: tags,
             score: score,
             createdAt: new Date(createdAt) };
}


export type EntryInfo = {
    readonly title: string;
    readonly body: string;
    readonly url: URL;
    readonly publishedAt: Date;
}


export function entryInfoFromJSON({ title, body, url, publishedAt }:
                                  { title: string, body: string, url: string, publishedAt: string }): EntryInfo {
    return { title,
             body,
             url: toURL(url),
             publishedAt: new Date(publishedAt) };
}


export type FeedInfo = {
    readonly url: URL;
    readonly title: string;
    readonly description: string;
    readonly entries: EntryInfo[];
};


export function feedInfoFromJSON({ url, title, description, entries }:
                                 { url: string, title: string, description: string, entries: any[] }): FeedInfo {
    return { url: toURL(url),
             title,
             description,
             entries: entries.map(entryInfoFromJSON) };
}


export type TagInfo = {
    readonly uid: string;
    readonly name: string|null;
    readonly link: string|null;
    readonly categories: string[];
};


export function tagInfoFromJSON({ uid, name, link, categories }:
                                { uid: string, name: string|null, link: string|null, categories: string[] }): TagInfo {
    return { uid,
             name: name,
             link: link,
             categories };
}


export function noInfoTag(uid: string): TagInfo {
    return { uid,
             name: null,
             link: null,
             categories: [] };
}


export type UserSetting = {
    readonly kind: string;
    readonly type: string;
    value: string|number|boolean;
    readonly name: string;
}


export function userSettingFromJSON({ kind, type, value, name }:
                                    { kind: string, type: string, value: string|number|boolean, name: string }): UserSetting {
    return { kind,
             type,
             value,
             name };
}
