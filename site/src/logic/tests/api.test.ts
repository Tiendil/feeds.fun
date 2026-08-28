import {afterEach, describe, expect, it, vi} from "vitest";

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

import {getProductState, getResourceStatistics} from "@/logic/api";

describe("getProductState", () => {
  afterEach(() => {
    mocks.post.mockReset();
  });

  it("requests and parses the current token balances", async () => {
    mocks.post.mockResolvedValue({
      data: {
        subscriptions: [
          {
            status: e.SubscriptionStatus.Active,
            startedAt: "2026-07-01T00:00:00Z",
            periodStartsAt: "2026-08-01T00:00:00Z",
            periodEndsAt: "2026-09-01T00:00:00Z",
            expectedRenewalAt: "2026-09-01T00:00:00Z",
            endsAt: null
          }
        ],
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
      }
    });

    const productState = await getProductState();

    expect(mocks.post).toHaveBeenCalledWith("/get-product-state", {}, undefined);
    expect(productState.subscriptions).toEqual([
      {
        status: e.SubscriptionStatus.Active,
        startedAt: new Date("2026-07-01T00:00:00Z"),
        periodStartsAt: new Date("2026-08-01T00:00:00Z"),
        periodEndsAt: new Date("2026-09-01T00:00:00Z"),
        expectedRenewalAt: new Date("2026-09-01T00:00:00Z"),
        endsAt: null
      }
    ]);
    expect(productState.tokens[e.ResourceKind.DayTokenUsage]).toEqual({
      limit: 1000,
      balance: 750,
      periodStartsAt: new Date("2026-08-10T00:00:00Z"),
      periodEndsAt: new Date("2026-08-11T00:00:00Z")
    });
    expect(productState.tokens[e.ResourceKind.LifetimeTokenUsage]).toEqual({
      limit: null,
      balance: 500,
      periodStartsAt: null,
      periodEndsAt: null
    });
  });
});

describe("getResourceStatistics", () => {
  afterEach(() => {
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
        interval: "year",
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
      interval: "year"
    });

    expect(mocks.post).toHaveBeenCalledWith(
      "/get-resource-statistics",
      {
        kinds,
        interval: "year"
      },
      undefined
    );
    expect(statistics).toEqual({
      interval: "year",
      statistics: {
        [e.ResourceKind.LifetimeTokenUsage]: {
          firstDate: new Date("2024-01-01T00:00:00Z"),
          values: [12]
        }
      }
    });
  });
});
