
export type FeedId = string & { readonly __brand: unique symbol };

export function toFeedId(id: string): FeedId {
    return id as FeedId;
}

export type URL = string & { readonly __brand: unique symbol };

export function toURL(url: string): URL {
    return url as URL;
}

export type Feed = {
    readonly id: FeedId;
    readonly url: URL;
    readonly loadedAt: Date;
};


export function feedFromJSON({ id, url, loadedAt }: { id: string, url: string, loadedAt: string }): Feed {
    return { id: toFeedId(id),
             url: toURL(url),
             loadedAt: new Date(loadedAt) };
}
