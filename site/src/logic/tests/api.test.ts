import {beforeEach, describe, expect, it, vi} from "vitest";

import * as e from "@/logic/enums";

const mocks = vi.hoisted(() => ({
  post: vi.fn()
}));

vi.mock("axios", () => ({
  default: {
    create: vi.fn(() => ({
      post: mocks.post,
      interceptors: {response: {use: vi.fn()}}
    }))
  }
}));

import {getResourceStatistics} from "@/logic/api";

describe("getResourceStatistics", () => {
  beforeEach(() => {
    mocks.post.mockReset();
  });

  it("sends all kinds and parses the compact response", async () => {
    const kinds = [
      e.ResourceKind.TokensCost,
      e.ResourceKind.DayTokenUsage,
      e.ResourceKind.MonthTokenUsage,
      e.ResourceKind.LifetimeTokenUsage
    ];
    mocks.post.mockResolvedValue({
      data: {
        interval: e.ResourceStatisticsInterval.Year,
        statistics: {
          [e.ResourceKind.LifetimeTokenUsage]: {
            firstDate: "2024-01-01",
            values: ["12"]
          }
        }
      }
    });

    const statistics = await getResourceStatistics({
      kinds,
      interval: e.ResourceStatisticsInterval.Year
    });

    expect(mocks.post).toHaveBeenCalledWith(
      "/get-resource-statistics",
      {
        kinds,
        interval: e.ResourceStatisticsInterval.Year
      },
      undefined
    );
    expect(statistics).toEqual({
      interval: e.ResourceStatisticsInterval.Year,
      statistics: {
        [e.ResourceKind.LifetimeTokenUsage]: {
          firstDate: new Date("2024-01-01T00:00:00Z"),
          values: [12]
        }
      }
    });
  });
});
