import {describe, expect, it} from "vitest";

import {discoverySectionIds, settingsSectionIds} from "@/logic/navigation";

describe("navigation section IDs", () => {
  it("defines the hash-free fragment values", () => {
    expect(discoverySectionIds).toEqual({
      addFeed: "add-feed",
      importOPML: "import-opml"
    });
    expect(settingsSectionIds).toEqual({
      general: "settings-general",
      subscriptions: "settings-subscriptions",
      messages: "settings-messages",
      personalFeedTagging: "settings-personal-feed-tagging",
      apiKeys: "settings-api-keys",
      apiKeyUsage: "settings-api-key-usage",
      tokenUsage: "settings-token-usage",
      dangerZone: "settings-danger-zone"
    });
  });
});
