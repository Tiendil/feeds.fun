import * as c from "@/logic/constants";


export type AnyEnum = {
  [key in keyof any]: string | number;
}


export enum MainPanelMode {
    Entries = "entries",
    Feeds = "feeds",
    Rules = "rules",
    Discovery = "discovery",
}


export const MainPanelModeProperties = new Map<MainPanelMode, {text: string}>([
    [MainPanelMode.Entries, {text: "news"}],
    [MainPanelMode.Feeds, {text: "feeds"}],
    [MainPanelMode.Rules, {text: "rules"}],
    [MainPanelMode.Discovery, {text: "discovery"}],
]);


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
export const LastEntriesPeriodProperties = new Map<LastEntriesPeriod, {text: string, seconds: number}>([
    [LastEntriesPeriod.Hour1, {text: "1 hour", seconds: c.hour}],
    [LastEntriesPeriod.Hour3, {text: "3 hours", seconds: 3 * c.hour}],
    [LastEntriesPeriod.Hour6, {text: "6 hours", seconds: 6 * c.hour}],
    [LastEntriesPeriod.Hour12, {text: "12 hours", seconds: 12 * c.hour }],
    [LastEntriesPeriod.Day1, {text: "1 day", seconds: c.day }],
    [LastEntriesPeriod.Day3, {text: "3 days", seconds: 3 * c.day }],
    [LastEntriesPeriod.Week, {text: "1 week", seconds: c.week }],
    [LastEntriesPeriod.Week2, {text: "2 weeks", seconds: 2 * c.week }],
    [LastEntriesPeriod.Month1, {text: "1 month", seconds: c.month }]
]);


export enum EntriesOrder {
    Score = "score",
    ScoreToZero = "score-to-zero",
    Published = "published",
    Cataloged = "cataloged"
};


export const EntriesOrderProperties = new Map<EntriesOrder, {text: string, orderField: string, timeField}>([
    [EntriesOrder.Score, {text: "score", orderField: "score", timeField: "catalogedAt"}],
    [EntriesOrder.ScoreToZero, {text: "score ~ 0", orderField: "scoreToZero", timeField: "catalogedAt"}],
    [EntriesOrder.Published, {text: "published", orderField: "publishedAt", timeField: "publishedAt"}],
    [EntriesOrder.Cataloged, {text: "cataloged", orderField: "catalogedAt", timeField: "catalogedAt"}],
]);


export enum Marker {
    Read = "read"
};


export const reverseMarker = {
    "read": Marker.Read
};
