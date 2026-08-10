import {describe, expect, it} from "vitest";

import * as e from "@/logic/enums";
import {
  entryFromJSON,
  feedFromJSON,
  productStateFromJSON,
  resourceStatisticsFromJSON,
  type RawEntry,
  type RawFeed
} from "@/logic/types";

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

describe("resourceStatisticsFromJSON", () => {
  it("translates an empty statistics record", () => {
    expect(
      resourceStatisticsFromJSON({
        interval: "day",
        statistics: {}
      })
    ).toEqual({
      interval: "day",
      statistics: {}
    });
  });

  it("translates a resource series with no values", () => {
    const statistics = resourceStatisticsFromJSON({
      interval: "month",
      statistics: {
        [e.ResourceKind.TokensCost]: {firstDate: "2025-01-01", values: []}
      }
    });

    expect(statistics.statistics[e.ResourceKind.TokensCost]).toEqual({
      firstDate: new Date("2025-01-01T00:00:00Z"),
      values: []
    });
  });

  it("translates all resource series and the year interval", () => {
    const statistics = resourceStatisticsFromJSON({
      interval: "year",
      statistics: {
        [e.ResourceKind.TokensCost]: {firstDate: "2025-01-01", values: [0]},
        [e.ResourceKind.DayTokenUsage]: {firstDate: "2023-01-01", values: [1, "2.5", 0]},
        [e.ResourceKind.MonthTokenUsage]: {firstDate: "2025-01-01", values: [0]},
        [e.ResourceKind.LifetimeTokenUsage]: {firstDate: "2024-01-01", values: ["7"]}
      }
    });

    expect(statistics.interval).toBe("year");
    expect(statistics.statistics[e.ResourceKind.TokensCost]).toEqual({
      firstDate: new Date("2025-01-01T00:00:00Z"),
      values: [0]
    });
    expect(statistics.statistics[e.ResourceKind.DayTokenUsage]).toEqual({
      firstDate: new Date("2023-01-01T00:00:00Z"),
      values: [1, 2.5, 0]
    });
    expect(statistics.statistics[e.ResourceKind.MonthTokenUsage]).toEqual({
      firstDate: new Date("2025-01-01T00:00:00Z"),
      values: [0]
    });
    expect(statistics.statistics[e.ResourceKind.LifetimeTokenUsage]).toEqual({
      firstDate: new Date("2024-01-01T00:00:00Z"),
      values: [7]
    });
  });
});

describe("productStateFromJSON", () => {
  it("parses recurring periods and preserves lifetime nulls", () => {
    const productState = productStateFromJSON({
      tokens: {
        day: {
          limit: 1000,
          balance: 750,
          periodStartsAt: "2026-08-10T00:00:00Z",
          periodEndsAt: "2026-08-11T00:00:00Z"
        },
        month: {
          limit: 10000,
          balance: 8000,
          periodStartsAt: "2026-08-01T00:00:00Z",
          periodEndsAt: "2026-09-01T00:00:00Z"
        },
        lifetime: {
          limit: null,
          balance: 500,
          periodStartsAt: null,
          periodEndsAt: null
        }
      }
    });

    expect(productState.tokens).toEqual({
      [e.ResourceKind.DayTokenUsage]: {
        limit: 1000,
        balance: 750,
        periodStartsAt: new Date("2026-08-10T00:00:00Z"),
        periodEndsAt: new Date("2026-08-11T00:00:00Z")
      },
      [e.ResourceKind.MonthTokenUsage]: {
        limit: 10000,
        balance: 8000,
        periodStartsAt: new Date("2026-08-01T00:00:00Z"),
        periodEndsAt: new Date("2026-09-01T00:00:00Z")
      },
      [e.ResourceKind.LifetimeTokenUsage]: {
        limit: null,
        balance: 500,
        periodStartsAt: null,
        periodEndsAt: null
      }
    });
  });
});
