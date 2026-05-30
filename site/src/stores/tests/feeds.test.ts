import {createPinia, setActivePinia} from "pinia";
import {beforeEach, describe, expect, it, vi} from "vitest";

import * as api from "@/logic/api";
import * as t from "@/logic/types";
import {useFeedsStore} from "@/stores/feeds";

const timerInstances = vi.hoisted(() => [] as Array<{refresher: () => Promise<void>; delay: number}>);

vi.mock("@/logic/timer", () => ({
  Timer: vi.fn().mockImplementation((refresher, delay) => {
    timerInstances.push({refresher, delay});

    return {
      start: vi.fn(),
      stop: vi.fn()
    };
  })
}));

vi.mock("@/stores/globalSettings", () => ({
  useGlobalSettingsStore: vi.fn(() => ({
    dataVersion: 0
  }))
}));

vi.mock("@/logic/api", () => ({
  addFeed: vi.fn(),
  getFeeds: vi.fn(),
  getFeedsByIds: vi.fn(),
  unsubscribe: vi.fn()
}));

function feed(overrides: Partial<t.RawFeed> = {}) {
  return t.feedFromJSON({
    id: "dca40ac1-73da-49dc-b7d8-40dac312ae40",
    title: "Feed",
    description: "Feed description",
    url: "https://example.com/feed",
    siteUrl: "https://example.com",
    state: "loaded",
    collectionIds: [],
    young: false,
    entriesPerDay: 3,
    ...overrides
  });
}

async function settleAsyncWork() {
  await Promise.resolve();
  await Promise.resolve();
  await Promise.resolve();
}

describe("useFeedsStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    timerInstances.length = 0;
    setActivePinia(createPinia());

    vi.mocked(api.addFeed).mockResolvedValue(feed());
    vi.mocked(api.getFeeds).mockResolvedValue([]);
    vi.mocked(api.getFeedsByIds).mockResolvedValue([]);
    vi.mocked(api.unsubscribe).mockResolvedValue(undefined);
  });

  it("loads feed list and preserves already loaded details from storage", async () => {
    const feedId = t.toFeedId("dca40ac1-73da-49dc-b7d8-40dac312ae40");

    vi.mocked(api.addFeed).mockResolvedValue(feed({entriesLoadedDetails: [1, 0, 3]}));
    vi.mocked(api.getFeeds).mockResolvedValue([feed({entriesLoadedDetails: null})]);

    const store = useFeedsStore();

    await store.subscribe(t.toURL("https://example.com/feed"));

    expect(store.feeds[feedId].entriesLoadedDetails).toEqual([1, 0, 3]);

    store.loadedFeedsReport;
    await settleAsyncWork();

    expect(store.loadedFeedsReport).toEqual([feedId]);
    expect(store.feeds[feedId].entriesLoadedDetails).toEqual([1, 0, 3]);
  });

  it("loads full feed data for displayed feed only once", async () => {
    const feedId = t.toFeedId("dca40ac1-73da-49dc-b7d8-40dac312ae40");
    const store = useFeedsStore();

    await store.subscribe(t.toURL("https://example.com/feed"));

    vi.mocked(api.getFeedsByIds).mockResolvedValue([feed({entriesLoadedDetails: [2, 4]})]);

    store.displayFeed({feedId});

    expect(store.displayedFeedId).toBe(feedId);

    await timerInstances[0].refresher();

    expect(api.getFeedsByIds).toHaveBeenCalledWith({ids: [feedId]});
    expect(store.feeds[feedId].entriesLoadedDetails).toEqual([2, 4]);

    vi.mocked(api.getFeedsByIds).mockClear();

    store.requestFullFeed({feedId});

    await timerInstances[0].refresher();

    expect(api.getFeedsByIds).not.toHaveBeenCalled();
  });

  it("keeps full feed request queued when API loading fails", async () => {
    const feedId = t.toFeedId("dca40ac1-73da-49dc-b7d8-40dac312ae40");
    const store = useFeedsStore();

    await store.subscribe(t.toURL("https://example.com/feed"));

    vi.mocked(api.getFeedsByIds).mockRejectedValueOnce(new Error("load failed"));

    store.requestFullFeed({feedId});

    await expect(timerInstances[0].refresher()).rejects.toThrow("load failed");

    vi.mocked(api.getFeedsByIds).mockResolvedValueOnce([feed({entriesLoadedDetails: [7]})]);

    await timerInstances[0].refresher();

    expect(api.getFeedsByIds).toHaveBeenLastCalledWith({ids: [feedId]});
    expect(store.feeds[feedId].entriesLoadedDetails).toEqual([7]);
  });

  it("hides only the currently displayed feed", () => {
    const feedId = t.toFeedId("dca40ac1-73da-49dc-b7d8-40dac312ae40");
    const anotherFeedId = t.toFeedId("dca40ac1-73da-49dc-b7d8-40dac312ae41");
    const store = useFeedsStore();

    store.displayFeed({feedId});

    store.hideFeed({feedId: anotherFeedId});

    expect(store.displayedFeedId).toBe(feedId);

    store.hideFeed({feedId});

    expect(store.displayedFeedId).toBeNull();
  });

  it("removes unsubscribed feeds from storage", async () => {
    const feedId = t.toFeedId("dca40ac1-73da-49dc-b7d8-40dac312ae40");
    const store = useFeedsStore();

    await store.subscribe(t.toURL("https://example.com/feed"));

    expect(store.feeds[feedId]).toBeDefined();

    await store.unsubscribe(feedId);

    expect(api.unsubscribe).toHaveBeenCalledWith({feedId});
    expect(store.feeds[feedId]).toBeUndefined();
  });
});
