import {createPinia, setActivePinia} from "pinia";
import {beforeEach, describe, expect, it, vi} from "vitest";

import * as api from "@/logic/api";
import * as t from "@/logic/types";
import {useCollectionsStore} from "@/stores/collections";

const updateDataVersion = vi.hoisted(() => vi.fn());

vi.mock("@/stores/globalSettings", () => ({
  useGlobalSettingsStore: vi.fn(() => ({
    updateDataVersion
  }))
}));

vi.mock("@/logic/api", () => ({
  getCollections: vi.fn(),
  getCollectionFeeds: vi.fn(),
  subscribeToCollections: vi.fn()
}));

describe("useCollectionsStore", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setActivePinia(createPinia());

    vi.mocked(api.getCollections).mockResolvedValue([]);
    vi.mocked(api.getCollectionFeeds).mockResolvedValue([]);
    vi.mocked(api.subscribeToCollections).mockResolvedValue(undefined);
  });

  it("refreshes application data after subscribing to collections", async () => {
    const collectionsIds = [t.toCollectionId("collection-1"), t.toCollectionId("collection-2")];
    const store = useCollectionsStore();

    await store.subscribe({collectionsIds});

    expect(api.subscribeToCollections).toHaveBeenCalledWith({collectionsIds});
    expect(updateDataVersion).toHaveBeenCalledOnce();
  });

  it("does not refresh application data when subscribing fails", async () => {
    const error = new Error("subscription failed");
    const store = useCollectionsStore();

    vi.mocked(api.subscribeToCollections).mockRejectedValueOnce(error);

    await expect(store.subscribe({collectionsIds: [t.toCollectionId("collection-1")]})).rejects.toBe(error);

    expect(updateDataVersion).not.toHaveBeenCalled();
  });
});
