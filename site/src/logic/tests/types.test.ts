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
    entriesLoaded: 7,
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
  it("translates linked date and entry loading details", () => {
    const feed = feedFromJSON(
      rawFeed({
        linkedAt: "2026-05-11T12:00:00Z",
        entriesLoadedDetails: [1, 0, 3]
      })
    );

    expect(feed.linkedAt).toEqual(new Date("2026-05-11T12:00:00Z"));
    expect(feed.entriesLoadedDetails).toEqual([1, 0, 3]);
  });

  it("uses null defaults for missing optional response values", () => {
    const feed = feedFromJSON(rawFeed());

    expect(feed.linkedAt).toBeNull();
    expect(feed.entriesLoadedDetails).toBeNull();
  });

  it("keeps null optional response values as null", () => {
    const feed = feedFromJSON(
      rawFeed({
        linkedAt: null,
        entriesLoadedDetails: null
      })
    );

    expect(feed.linkedAt).toBeNull();
    expect(feed.entriesLoadedDetails).toBeNull();
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
