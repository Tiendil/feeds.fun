import {describe, expect, it} from "vitest";

import * as e from "@/logic/enums";
import {
  assertTokenUsageStatistics,
  emptyTokenUsageStatistics,
  tokenUsageSlots,
  type TokenUsageStatisticsData
} from "@/logic/resourceStatistics";
import type * as t from "@/logic/types";

function statistics(
  granularity: e.TimeGranularity,
  series: Partial<TokenUsageStatisticsData["statistics"]> = {}
): TokenUsageStatisticsData {
  const noUsage = {
    firstDate: new Date("2100-01-01T00:00:00Z"),
    values: [0]
  };

  return {
    interval: e.TimeGranularityProperties.get(granularity)!.resourceApiId,
    statistics: {
      [e.ResourceKind.DayTokenUsage]: noUsage,
      [e.ResourceKind.MonthTokenUsage]: noUsage,
      [e.ResourceKind.LifetimeTokenUsage]: noUsage,
      ...series
    }
  };
}

function isoDate(date: Date): string {
  return date.toISOString().slice(0, 10);
}

describe("assertTokenUsageStatistics", () => {
  it("accepts a response with all requested token series", () => {
    expect(() => assertTokenUsageStatistics(statistics(e.TimeGranularity.Day))).not.toThrow();
  });

  it("rejects a response that omits a requested token series", () => {
    const incompleteStatistics: t.ResourceStatistics = {
      interval: "day",
      statistics: {
        [e.ResourceKind.DayTokenUsage]: {
          firstDate: new Date("2026-08-05T00:00:00Z"),
          values: [0]
        }
      }
    };

    expect(() => assertTokenUsageStatistics(incompleteStatistics)).toThrow(
      "Missing requested resource statistics series: month_token_usage"
    );
  });
});

describe("emptyTokenUsageStatistics", () => {
  it.each([
    {
      granularity: e.TimeGranularity.Day,
      interval: "day",
      expectedFirstDate: "2026-08-20T00:00:00Z",
      rangeFirstDate: "2026-08-18T00:00:00Z",
      rangeLastDate: "2026-08-20T23:59:59Z"
    },
    {
      granularity: e.TimeGranularity.Month,
      interval: "month",
      expectedFirstDate: "2026-08-01T00:00:00Z",
      rangeFirstDate: "2026-06-01T00:00:00Z",
      rangeLastDate: "2026-08-31T23:59:59Z"
    },
    {
      granularity: e.TimeGranularity.Year,
      interval: "year",
      expectedFirstDate: "2026-01-01T00:00:00Z",
      rangeFirstDate: "2024-01-01T00:00:00Z",
      rangeLastDate: "2026-12-31T23:59:59Z"
    }
  ])(
    "creates empty $granularity series aligned to the requested interval",
    ({granularity, interval, expectedFirstDate, rangeFirstDate, rangeLastDate}) => {
      const result = emptyTokenUsageStatistics(granularity, new Date("2026-08-20T08:30:00Z"));

      expect(result.interval).toBe(interval);

      for (const kind of [
        e.ResourceKind.DayTokenUsage,
        e.ResourceKind.MonthTokenUsage,
        e.ResourceKind.LifetimeTokenUsage
      ]) {
        expect(result.statistics[kind]).toEqual({
          firstDate: new Date(expectedFirstDate),
          values: []
        });
      }

      const slots = tokenUsageSlots({
        statistics: result,
        granularity,
        firstDate: new Date(rangeFirstDate),
        lastDate: new Date(rangeLastDate)
      });

      expect(slots).toHaveLength(3);
      expect(slots.every((slot) => Object.values(slot.values).every((value) => value === 0))).toBe(true);
    }
  );
});

describe("tokenUsageSlots", () => {
  it("aligns independent daily series and pads an explicit date range", () => {
    const slots = tokenUsageSlots({
      statistics: statistics(e.TimeGranularity.Day, {
        [e.ResourceKind.DayTokenUsage]: {
          firstDate: new Date("2026-07-06T00:00:00Z"),
          values: [9, 2]
        },
        [e.ResourceKind.MonthTokenUsage]: {
          firstDate: new Date("2026-08-04T00:00:00Z"),
          values: [3, 4]
        }
      }),
      granularity: e.TimeGranularity.Day,
      firstDate: new Date("2026-07-07T00:00:00Z"),
      lastDate: new Date("2026-08-05T19:30:00Z")
    });

    expect(slots).toHaveLength(30);
    expect(isoDate(slots[0].date)).toBe("2026-07-07");
    expect(isoDate(slots[29].date)).toBe("2026-08-05");
    expect(slots[0].values).toEqual({
      [e.ResourceKind.DayTokenUsage]: 2,
      [e.ResourceKind.MonthTokenUsage]: 0,
      [e.ResourceKind.LifetimeTokenUsage]: 0
    });
    expect(slots[28].values[e.ResourceKind.MonthTokenUsage]).toBe(3);
    expect(slots[29].values[e.ResourceKind.MonthTokenUsage]).toBe(4);
    expect(slots[29].values[e.ResourceKind.DayTokenUsage]).toBe(0);
  });

  it("aligns independent series across an explicit history range", () => {
    const slots = tokenUsageSlots({
      statistics: statistics(e.TimeGranularity.Day, {
        [e.ResourceKind.DayTokenUsage]: {
          firstDate: new Date("2026-06-01T00:00:00Z"),
          values: [11]
        },
        [e.ResourceKind.MonthTokenUsage]: {
          firstDate: new Date("2025-01-01T00:00:00Z"),
          values: []
        },
        [e.ResourceKind.LifetimeTokenUsage]: {
          firstDate: new Date("2026-07-01T00:00:00Z"),
          values: [7]
        }
      }),
      granularity: e.TimeGranularity.Day,
      firstDate: new Date("2026-06-01T00:00:00Z"),
      lastDate: new Date("2026-08-05T12:00:00Z")
    });

    expect(isoDate(slots[0].date)).toBe("2026-06-01");
    expect(isoDate(slots.at(-1)!.date)).toBe("2026-08-05");
    expect(slots[0].values[e.ResourceKind.DayTokenUsage]).toBe(11);
    expect(slots[30].values[e.ResourceKind.LifetimeTokenUsage]).toBe(7);
    expect(slots.at(-1)!.values[e.ResourceKind.LifetimeTokenUsage]).toBe(0);
  });

  it("uses a 12-month explicit range across a year boundary", () => {
    const slots = tokenUsageSlots({
      statistics: statistics(e.TimeGranularity.Month, {
        [e.ResourceKind.DayTokenUsage]: {
          firstDate: new Date("2025-12-01T00:00:00Z"),
          values: [5, 8]
        }
      }),
      granularity: e.TimeGranularity.Month,
      firstDate: new Date("2025-09-01T00:00:00Z"),
      lastDate: new Date("2026-08-20T08:00:00Z")
    });

    expect(slots).toHaveLength(12);
    expect(isoDate(slots[0].date)).toBe("2025-09-01");
    expect(isoDate(slots.at(-1)!.date)).toBe("2026-08-01");
    expect(slots[3].values[e.ResourceKind.DayTokenUsage]).toBe(5);
    expect(slots[4].values[e.ResourceKind.DayTokenUsage]).toBe(8);
  });

  it("uses a 12-year explicit range", () => {
    const slots = tokenUsageSlots({
      statistics: statistics(e.TimeGranularity.Year, {
        [e.ResourceKind.DayTokenUsage]: {
          firstDate: new Date("2020-06-01T00:00:00Z"),
          values: [5, 8]
        }
      }),
      granularity: e.TimeGranularity.Year,
      firstDate: new Date("2015-01-01T00:00:00Z"),
      lastDate: new Date("2026-08-20T08:00:00Z")
    });

    expect(slots).toHaveLength(12);
    expect(isoDate(slots[0].date)).toBe("2015-01-01");
    expect(isoDate(slots.at(-1)!.date)).toBe("2026-01-01");
    expect(slots[5].values[e.ResourceKind.DayTokenUsage]).toBe(5);
    expect(slots[6].values[e.ResourceKind.DayTokenUsage]).toBe(8);
  });

  it("preserves leap day while advancing UTC dates", () => {
    const slots = tokenUsageSlots({
      statistics: statistics(e.TimeGranularity.Day, {
        [e.ResourceKind.DayTokenUsage]: {
          firstDate: new Date("2024-02-28T00:00:00Z"),
          values: [1, 2, 3]
        }
      }),
      granularity: e.TimeGranularity.Day,
      firstDate: new Date("2024-02-28T00:00:00Z"),
      lastDate: new Date("2024-03-01T23:59:59Z")
    });

    expect(slots.slice(-3).map((slot) => isoDate(slot.date))).toEqual(["2024-02-28", "2024-02-29", "2024-03-01"]);
    expect(slots.slice(-3).map((slot) => slot.values[e.ResourceKind.DayTokenUsage])).toEqual([1, 2, 3]);
  });

  it("uses the explicit range for empty statistics", () => {
    const slots = tokenUsageSlots({
      statistics: statistics(e.TimeGranularity.Day),
      granularity: e.TimeGranularity.Day,
      firstDate: new Date("2026-08-03T18:00:00Z"),
      lastDate: new Date("2026-08-05T12:00:00Z")
    });

    expect(slots.map((slot) => isoDate(slot.date))).toEqual(["2026-08-03", "2026-08-04", "2026-08-05"]);
  });
});
