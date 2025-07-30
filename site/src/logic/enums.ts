import * as c from "@/logic/constants";
import * as settings from "@/logic/settings";

export type AnyEnum = {
  [key in keyof any]: string | number;
};

///////////////////
// Main panel modes
///////////////////

export enum MainPanelMode {
  Entries = "entries",
  Feeds = "feeds",
  Rules = "rules",
  Discovery = "discovery",
  Collections = "collections",
  PublicCollection = "public-collection",
  Settings = "settings"
}

export type MainPanelModeProperty = {
  readonly text: string;
  readonly showInMenu: boolean;
};

export const MainPanelModeProperties = new Map<MainPanelMode, MainPanelModeProperty>([
  [MainPanelMode.Entries, {text: "News", showInMenu: true}],
  [MainPanelMode.Feeds, {text: "Feeds", showInMenu: true}],
  [MainPanelMode.Rules, {text: "Rules", showInMenu: true}],
  [MainPanelMode.Discovery, {text: "Discovery", showInMenu: true}],
  [MainPanelMode.Collections, {text: "Collections", showInMenu: settings.hasCollections}],
  [MainPanelMode.PublicCollection, {text: "Public Collection", showInMenu: false}],
  [MainPanelMode.Settings, {text: "Settings", showInMenu: true}]
]);

//////////////////////
// Last entries period
//////////////////////

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
  Month3 = "month3",
  Month6 = "month6",
  Year1 = "year1",
  AllTime = "alltime"
}

export type LastEntriesPeriodProperty = {
  readonly text: string;
  readonly seconds: number;
};

// Map preserves the order of the keys
export const LastEntriesPeriodProperties = new Map<LastEntriesPeriod, LastEntriesPeriodProperty>([
  [LastEntriesPeriod.Hour1, {text: "1 hour", seconds: c.hour}],
  [LastEntriesPeriod.Hour3, {text: "3 hours", seconds: 3 * c.hour}],
  [LastEntriesPeriod.Hour6, {text: "6 hours", seconds: 6 * c.hour}],
  [LastEntriesPeriod.Hour12, {text: "12 hours", seconds: 12 * c.hour}],
  [LastEntriesPeriod.Day1, {text: "1 day", seconds: c.day}],
  [LastEntriesPeriod.Day3, {text: "3 days", seconds: 3 * c.day}],
  [LastEntriesPeriod.Week, {text: "1 week", seconds: c.week}],
  [LastEntriesPeriod.Week2, {text: "2 weeks", seconds: 2 * c.week}],
  [LastEntriesPeriod.Month1, {text: "1 month", seconds: c.month}],
  [LastEntriesPeriod.Month3, {text: "3 months", seconds: 3 * c.month}],
  [LastEntriesPeriod.Month6, {text: "6 months", seconds: 6 * c.month}],
  [LastEntriesPeriod.Year1, {text: "1 year", seconds: c.year}],
  [LastEntriesPeriod.AllTime, {text: "all time", seconds: c.infinity}]
]);

////////////////
// Entries order
////////////////

export enum EntriesOrder {
  Score = "score",
  ScoreToZero = "score-to-zero",
  ScoreBackward = "score-to-",
  Published = "published",
  Cataloged = "cataloged"
}

export type EntriesOrderProperty = {
  readonly text: string;
  readonly orderField: string;
  readonly timeField: string;
  readonly direction: number;
};

export const EntriesOrderProperties = new Map<EntriesOrder, EntriesOrderProperty>([
  [EntriesOrder.Score, {text: "score", orderField: "score", timeField: "catalogedAt", direction: 1}],
  [EntriesOrder.ScoreToZero, {text: "score ~ 0", orderField: "scoreToZero", timeField: "catalogedAt", direction: 1}],
  [EntriesOrder.ScoreBackward, {text: "score backward", orderField: "score", timeField: "catalogedAt", direction: -1}],
  [EntriesOrder.Published, {text: "published", orderField: "publishedAt", timeField: "publishedAt", direction: 1}],
  [EntriesOrder.Cataloged, {text: "cataloged", orderField: "catalogedAt", timeField: "catalogedAt", direction: 1}]
]);

////////////////
// Min news tag count
////////////////

export enum MinNewsTagCount {
  One = "one",
  Two = "two",
  Three = "three",
  Four = "four",
  Five = "five",
}

export type MinNewsTagCountProperty = {
  readonly text: string;
  readonly count: number;
};

export const MinNewsTagCountProperties = new Map<MinNewsTagCount, MinNewsTagCountProperty>([
  [MinNewsTagCount.One, {text: "all", count: 1}],
  [MinNewsTagCount.Two, {text: "if in 2+ news", count: 2}],
  [MinNewsTagCount.Three, {text: "if in 3+ news", count: 3}],
  [MinNewsTagCount.Four, {text: "if in 4+ news", count: 4}],
  [MinNewsTagCount.Five, {text: "if in 5+ news", count: 5}]
]);


/////////
// Marker
/////////

export enum Marker {
  Read = "read"
}

export const reverseMarker: {[key: string]: Marker} = {
  read: Marker.Read
};

//////////////
// Feeds order
//////////////

export enum FeedsOrder {
  Title = "title",
  Url = "url",
  Loaded = "loaded",
  Linked = "linked"
}

export const FeedsOrderProperties = new Map<FeedsOrder, {text: string; orderField: string; orderDirection: string}>([
  [FeedsOrder.Title, {text: "title", orderField: "title", orderDirection: "asc"}],
  [FeedsOrder.Url, {text: "url", orderField: "url", orderDirection: "asc"}],
  [FeedsOrder.Loaded, {text: "loaded", orderField: "loadedAt", orderDirection: "desc"}],
  [FeedsOrder.Linked, {text: "added", orderField: "linkedAt", orderDirection: "desc"}]
]);

//////////////
// Rules order
//////////////

export enum RulesOrder {
  Tags = "tags",
  Score = "score",
  Created = "created",
  Updated = "updated"
}

export const RulesOrderProperties = new Map<RulesOrder, {text: string; orderField: string; orderDirection: string}>([
  [RulesOrder.Tags, {text: "tags", orderField: "tags", orderDirection: "asc"}],
  [RulesOrder.Score, {text: "score", orderField: "score", orderDirection: "desc"}],
  [RulesOrder.Created, {text: "created", orderField: "createdAt", orderDirection: "desc"}],
  [RulesOrder.Updated, {text: "updated", orderField: "updatedAt", orderDirection: "desc"}]
]);
