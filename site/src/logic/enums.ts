export type AnyEnum = {
  [key in keyof any]: string | number;
}


export type AnyEnumText = {
  [key in keyof any]: string;
}

export enum MainPanelMode {
  News = "news",
  Feeds = "feeds",
}


export const MainPanelModeTexts = {
    [MainPanelMode.News]: "news",
    [MainPanelMode.Feeds]: "feeds",
}


export enum LastEntriesPeriod {
    Hour1 = "hour1",
    Hour3 = "hour3",
    Hour6 = "hour6",
    Hour12 = "hour12",
    Day1 = "day1",
    Day3 = "day3",
    Week = "week",
    Week2 = "week2",
    Month1 = "month",
}


// Map preserves the order of the keys
export const LastEntriesPeriodTexts = new Map<LastEntriesPeriod, string>([
    [LastEntriesPeriod.Hour1, "1 hour"],
    [LastEntriesPeriod.Hour3, "3 hours"],
    [LastEntriesPeriod.Hour6, "6 hours"],
    [LastEntriesPeriod.Hour12, "12 hours"],
    [LastEntriesPeriod.Day1, "1 day"],
    [LastEntriesPeriod.Day3, "3 days"],
    [LastEntriesPeriod.Week, "1 week"],
    [LastEntriesPeriod.Week2, "2 weeks"],
    [LastEntriesPeriod.Month1, "1 month"]]);
