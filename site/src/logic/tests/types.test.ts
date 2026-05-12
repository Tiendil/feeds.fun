import {describe, expect, it} from "vitest";

import * as e from "@/logic/enums";
import {entryFromJSON, type RawEntry} from "@/logic/types";

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

describe("entryFromJSON", () => {
  it("translates integer markers to frontend enum values", () => {
    const entry = entryFromJSON(rawEntry([1, 2]), {});

    expect(entry.markers).toEqual([e.Marker.Read, e.Marker.CanSeeTags]);
  });

  it("rejects unknown integer markers", () => {
    expect(() => entryFromJSON(rawEntry([100]), {})).toThrow("Unknown marker: 100");
  });
});
