import {describe, expect, it} from "vitest";

import * as e from "@/logic/enums";
import {entryFromJSON, feedFromJSON, type RawEntry, type RawFeed} from "@/logic/types";

function rawFeed(overrides: Partial<RawFeed> = {}): RawFeed {
  return {
    id: "dca40ac1-73da-49dc-b7d8-40dac312ae40",
    title: "Feed",
    description: "Feed description",
    url: "https://example.com/feed",
    state: "loaded",
    collectionIds: [],
    young: true,
    entriesPerDay: 7,
    ...overrides
  };
}

function rawEntry(markers: number[]): RawEntry {
  return {
    id: "ed278ccf-f8e3-4e8b-b065-1ad120444b47",
    feedId: "dca40ac1-73da-49dc-b7d8-40dac312ae40",
    title: "Entry",
    url: "https://example.com/entry",
    tags: [],
    markers,
    score: 0,
    scoreContributions: {},
    publishedAt: "2026-05-11T12:00:00Z"
  };
}

describe("feedFromJSON", () => {
  it("translates loaded feed response", () => {
    const feed = feedFromJSON(
      rawFeed({
        loadedAt: "2026-05-10T12:00:00Z",
        linkedAt: "2026-05-11T12:00:00Z",
        siteUrl: "https://example.com",
        lastError: "network_connection_timeout",
        collectionIds: ["dca40ac1-73da-49dc-b7d8-40dac312ae41"],
        young: false,
        entriesPerDay: 3,
        entriesLoadedDetails: [1, 0, 3]
      })
    );

    expect(feed.id).toBe("dca40ac1-73da-49dc-b7d8-40dac312ae40");
    expect(feed.url).toBe("https://example.com/feed");
    expect(feed.siteUrl).toBe("https://example.com");
    expect(feed.state).toBe("loaded");
    expect(feed.lastError).toBe("network_connection_timeout");
    expect(feed.loadedAt).toEqual(new Date("2026-05-10T12:00:00Z"));
    expect(feed.linkedAt).toEqual(new Date("2026-05-11T12:00:00Z"));
    expect(feed.isOk).toBe(true);
    expect(feed.collectionIds).toEqual(["dca40ac1-73da-49dc-b7d8-40dac312ae41"]);
    expect(feed.young).toBe(false);
    expect(feed.entriesPerDay).toBe(3);
    expect(feed.entriesLoadedDetails).toEqual([1, 0, 3]);
  });

  it("uses null defaults for missing optional response values", () => {
    const feed = feedFromJSON(rawFeed());

    expect(feed.lastError).toBeNull();
    expect(feed.loadedAt).toBeNull();
    expect(feed.linkedAt).toBeNull();
    expect(feed.siteUrl).toBeNull();
    expect(feed.entriesLoadedDetails).toBeNull();
  });

  it("keeps null optional response values as null", () => {
    const feed = feedFromJSON(
      rawFeed({
        lastError: null,
        loadedAt: null,
        linkedAt: null,
        siteUrl: null,
        entriesLoadedDetails: null
      })
    );

    expect(feed.lastError).toBeNull();
    expect(feed.loadedAt).toBeNull();
    expect(feed.linkedAt).toBeNull();
    expect(feed.siteUrl).toBeNull();
    expect(feed.entriesLoadedDetails).toBeNull();
  });

  it("marks non-loaded feed as not ok", () => {
    const feed = feedFromJSON(rawFeed({state: "damaged"}));

    expect(feed.state).toBe("damaged");
    expect(feed.isOk).toBe(false);
  });
});

describe("entryFromJSON", () => {
  it("translates integer markers to frontend enum values", () => {
    const entry = entryFromJSON(rawEntry([1, 2]), {});

    expect(entry.markers).toEqual([e.Marker.Read, e.Marker.CanSeeTags]);
  });

  it("rejects unknown integer markers", () => {
    expect(() => entryFromJSON(rawEntry([100]), {})).toThrow("Unknown marker: 100");
  });
});
