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
    readonly url: URL;
    readonly state: string;
    readonly lastError: string|null;
    readonly loadedAt: Date|null;
};


export function feedFromJSON({ id, url, state, lastError, loadedAt }:
                             { id: string, url: string, state: string, lastError: string|null, loadedAt: string }): Feed {
    return { id: toFeedId(id),
             url: toURL(url),
             state: state,
             lastError: lastError,
             loadedAt: loadedAt !== null ? new Date(loadedAt) : null };
}


export type Entry = {
    readonly id: EntryId;
    readonly feedId: FeedId;
    readonly title: string;
    readonly url: URL;
    readonly tags: string[];
    readonly markers: e.Marker[];
    readonly score: number;
    readonly publishedAt: Date;
    readonly catalogedAt: Date;
    readonly body: string|null;
}


export function entryFromJSON({ id, feedId, title, url, tags, markers, score, publishedAt, catalogedAt, body }:
                              { id: string, feedId: string, title: string, url: string, tags: string[],
                                markers: string[], score: number,
                                publishedAt: string, catalogedAt: string, body: string|null }): Entry {
    return { id: toEntryId(id),
             feedId: toFeedId(feedId),
             title,
             url: toURL(url),
             tags: tags,
             markers: markers.map(m => e.reverseMarker[m]),
             score: score,
             publishedAt: new Date(publishedAt),
             catalogedAt: new Date(catalogedAt),
             body: body };
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
