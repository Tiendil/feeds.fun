import * as e from "@/logic/enums";
import type * as t from "@/logic/types";

export type TokenUsageResourceKind =
  | e.ResourceKind.DayTokenUsage
  | e.ResourceKind.MonthTokenUsage
  | e.ResourceKind.LifetimeTokenUsage;

export type TokenUsageTimeGranularity = e.TimeGranularity.Day | e.TimeGranularity.Month | e.TimeGranularity.Year;

export type TokenUsageSlot = {
  readonly date: Date;
  readonly values: Record<TokenUsageResourceKind, number>;
};

export type TokenUsageStatisticsData = Omit<t.ResourceStatistics, "statistics"> & {
  readonly statistics: t.ResourceStatistics["statistics"] & Record<TokenUsageResourceKind, t.ResourceStatisticsSeries>;
};

export const tokenUsageResourceKinds: readonly TokenUsageResourceKind[] = [
  e.ResourceKind.DayTokenUsage,
  e.ResourceKind.MonthTokenUsage,
  e.ResourceKind.LifetimeTokenUsage
];

export function assertTokenUsageStatistics(
  statistics: t.ResourceStatistics
): asserts statistics is TokenUsageStatisticsData {
  for (const kind of tokenUsageResourceKinds) {
    if (statistics.statistics[kind] === undefined) {
      throw new Error(`Missing requested resource statistics series: ${kind}`);
    }
  }
}

export function periodStart(date: Date, granularity: TokenUsageTimeGranularity): Date {
  if (granularity === e.TimeGranularity.Day) {
    return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate()));
  }

  if (granularity === e.TimeGranularity.Month) {
    return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), 1));
  }

  return new Date(Date.UTC(date.getUTCFullYear(), 0, 1));
}

export function emptyTokenUsageStatistics(
  granularity: TokenUsageTimeGranularity,
  date: Date
): TokenUsageStatisticsData {
  const firstDate = periodStart(date, granularity);
  const emptySeries = () => ({
    firstDate: new Date(firstDate.getTime()),
    values: []
  });

  return {
    interval: e.TimeGranularityProperties.get(granularity)!.resourceApiId,
    statistics: {
      [e.ResourceKind.DayTokenUsage]: emptySeries(),
      [e.ResourceKind.MonthTokenUsage]: emptySeries(),
      [e.ResourceKind.LifetimeTokenUsage]: emptySeries()
    }
  };
}

export function shiftDate(date: Date, offset: number, granularity: TokenUsageTimeGranularity): Date {
  if (granularity === e.TimeGranularity.Day) {
    return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate() + offset));
  }

  if (granularity === e.TimeGranularity.Month) {
    return new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + offset, 1));
  }

  return new Date(Date.UTC(date.getUTCFullYear() + offset, 0, 1));
}

function valuesByDate(
  series: t.ResourceStatisticsSeries,
  granularity: TokenUsageTimeGranularity
): Map<number, number> {
  const values = new Map<number, number>();

  let date = periodStart(series.firstDate, granularity);

  for (const value of series.values) {
    values.set(date.getTime(), value);
    date = shiftDate(date, 1, granularity);
  }

  return values;
}

export function tokenUsageSlots({
  statistics,
  granularity,
  firstDate,
  lastDate
}: {
  statistics: TokenUsageStatisticsData;
  granularity: TokenUsageTimeGranularity;
  firstDate: Date;
  lastDate: Date;
}): TokenUsageSlot[] {
  const firstSlotDate = periodStart(firstDate, granularity);
  const lastSlotDate = periodStart(lastDate, granularity);
  const values = new Map(
    tokenUsageResourceKinds.map((kind) => [kind, valuesByDate(statistics.statistics[kind], granularity)])
  );
  const slots: TokenUsageSlot[] = [];

  for (let date = firstSlotDate; date <= lastSlotDate; date = shiftDate(date, 1, granularity)) {
    const timestamp = date.getTime();

    slots.push({
      date,
      values: {
        [e.ResourceKind.DayTokenUsage]: values.get(e.ResourceKind.DayTokenUsage)?.get(timestamp) ?? 0,
        [e.ResourceKind.MonthTokenUsage]: values.get(e.ResourceKind.MonthTokenUsage)?.get(timestamp) ?? 0,
        [e.ResourceKind.LifetimeTokenUsage]: values.get(e.ResourceKind.LifetimeTokenUsage)?.get(timestamp) ?? 0
      }
    });
  }

  return slots;
}
