
export type FeedId = string & { readonly __brand: unique symbol };

export function toFeedId(id: string): FeedId {
    return id as FeedId;
}


export type EntryId = string & { readonly __brand: unique symbol };

export function toEntryId(id: string): EntryId {
    return id as EntryId;
}

export type URL = string & { readonly __brand: unique symbol };

export function toURL(url: string): URL {
    return url as URL;
}

export type Feed = {
    readonly id: FeedId;
    readonly url: URL;
    readonly loadedAt: Date|null;
};


export function feedFromJSON({ id, url, loadedAt }: { id: string, url: string, loadedAt: string }): Feed {
    return { id: toFeedId(id),
             url: toURL(url),
             loadedAt: loadedAt !== null ? new Date(loadedAt) : null };
}


export type Entry = {
    readonly id: EntryId;
    readonly feedId: FeedId;
    readonly title: string;
    readonly url: URL;
    readonly tags: string[];
    readonly score: number;
    readonly publishedAt: Date;
    readonly catalogedAt: Date;
    readonly body: string|null;
}


export function entryFromJSON({ id, feedId, title, url, tags, score, publishedAt, catalogedAt, body }:
                              { id: string, feedId: string, title: string, url: string, tags: string[], score: number,
                                publishedAt: string, catalogedAt: string, body: string|null }): Entry {
    return { id: toEntryId(id),
             feedId: toFeedId(feedId),
             title,
             url: toURL(url),
             tags: tags,
             score: score,
             publishedAt: new Date(publishedAt),
             catalogedAt: new Date(catalogedAt),
             body: body }
}
