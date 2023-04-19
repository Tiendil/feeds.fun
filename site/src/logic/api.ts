import * as _ from "lodash";
import axios from "axios";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";

const ENTRY_POINT = 'http://127.0.0.1:8000'

const API_GET_FEEDS = `${ENTRY_POINT}/api/get-feeds`;
const API_GET_LAST_ENTRIES = `${ENTRY_POINT}/api/get-last-entries`;
const API_GET_ENTRIES_BY_IDS = `${ENTRY_POINT}/api/get-entries-by-ids`;
const API_CREATE_RULE = `${ENTRY_POINT}/api/create-rule`;
const API_DELETE_RULE = `${ENTRY_POINT}/api/delete-rule`;
const API_UPDATE_RULE = `${ENTRY_POINT}/api/update-rule`;
const API_GET_RULES = `${ENTRY_POINT}/api/get-rules`;
const API_GET_SCORE_DETAILS = `${ENTRY_POINT}/api/get-score-details`;
const API_SET_MARKER = `${ENTRY_POINT}/api/set-marker`;
const API_REMOVE_MARKER = `${ENTRY_POINT}/api/remove-marker`;


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
