import * as _ from "lodash";
import axios from "axios";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";

const ENTRY_POINT = '/api'

const API_GET_FEEDS = `${ENTRY_POINT}/get-feeds`;
const API_GET_LAST_ENTRIES = `${ENTRY_POINT}/get-last-entries`;
const API_GET_ENTRIES_BY_IDS = `${ENTRY_POINT}/get-entries-by-ids`;
const API_CREATE_RULE = `${ENTRY_POINT}/create-rule`;
const API_DELETE_RULE = `${ENTRY_POINT}/delete-rule`;
const API_UPDATE_RULE = `${ENTRY_POINT}/update-rule`;
const API_GET_RULES = `${ENTRY_POINT}/get-rules`;
const API_GET_SCORE_DETAILS = `${ENTRY_POINT}/get-score-details`;
const API_SET_MARKER = `${ENTRY_POINT}/set-marker`;
const API_REMOVE_MARKER = `${ENTRY_POINT}/remove-marker`;
const API_DISCOVER_FEEDS = `${ENTRY_POINT}/discover-feeds`;
const API_ADD_FEED = `${ENTRY_POINT}/add-feed`;
const API_ADD_OPML = `${ENTRY_POINT}/add-opml`;
const API_UNSUBSCRIBE = `${ENTRY_POINT}/unsubscribe`;


async function post({url, data}: {url: string, data: any}) {
    try {
        const response = await axios.post(url, data);
        return response.data;
    } catch (error) {
        console.log(error);
        throw error;
    }
}


export async function getFeeds() {
    const response = await post({url: API_GET_FEEDS, data: {}});

    const feeds = [];

    for (let rawFeed of response.feeds) {
        const feed = t.feedFromJSON(rawFeed);
        feeds.push(feed);
    }

    return feeds;
}


export async function getLastEntries({period}: {period: number}) {
    const response = await post({url: API_GET_LAST_ENTRIES, data: {period: period}});

    const entries = [];

    for (let rawEntry of response.entries) {
        const entry = t.entryFromJSON(rawEntry);
        entries.push(entry);
    }

    return entries;
}


export async function getEntriesByIds({ids}: {ids: t.EntryId[]}) {
    const response = await post({url: API_GET_ENTRIES_BY_IDS, data: {ids: ids}});

    const entries = [];

    for (let rawEntry of response.entries) {
        const entry = t.entryFromJSON(rawEntry);
        entries.push(entry);
    }

    return entries;
}


export async function createRule({tags, score}: {tags: string[], score: number}) {
    const response = await post({url: API_CREATE_RULE, data: {tags: tags, score: score}});
    return response;
}


export async function deleteRule({id}: {id: t.RuleId}) {
    const response = await post({url: API_DELETE_RULE, data: {id: id}});
    return response;
}


export async function updateRule({id, tags, score}: {id: t.RuleId, tags: string[], score: number}) {
    const response = await post({url: API_UPDATE_RULE, data: {id: id, tags: tags, score: score}});
    return response;
}


export async function getRules() {
    const response = await post({url: API_GET_RULES, data: {}});

    const rules = [];

    for (let rawRule of response.rules) {
        const rule = t.ruleFromJSON(rawRule);
        rules.push(rule);
    }

    return rules;
}


export async function getScoreDetails({entryId}: {entryId: t.EntryId}) {
    const response = await post({url: API_GET_SCORE_DETAILS, data: {entryId: entryId}});

    const rules = [];

    for (let rawRule of response.rules) {
        const rule = t.ruleFromJSON(rawRule);
        rules.push(rule);
    }

    return rules;
}


export async function setMarker({entryId, marker}: {entryId: t.EntryId, marker: e.Marker}) {
    await post({url: API_SET_MARKER, data: {entryId: entryId, marker: marker}});
}


export async function removeMarker({entryId, marker}: {entryId: t.EntryId, marker: e.Marker}) {
    await post({url: API_REMOVE_MARKER, data: {entryId: entryId, marker: marker}});
}


export async function discoverFeeds({url}: {url: string}) {
    const response = await post({url: API_DISCOVER_FEEDS, data: {url: url}});

    const feeds = [];

    for (let rawFeed of response.feeds) {
        const feed = t.feedInfoFromJSON(rawFeed);
        feeds.push(feed);
    }

    return feeds;
}


export async function addFeed({url}: {url: string}) {
    await post({url: API_ADD_FEED, data: {url: url}});
}


export async function addOPML({content}: {content: string}) {
    await post({url: API_ADD_OPML, data: {content: content}});
}


export async function unsubscribe({feedId}: {feedId: t.FeedId}) {
    await post({url: API_UNSUBSCRIBE, data: {feedId: feedId}});
}
