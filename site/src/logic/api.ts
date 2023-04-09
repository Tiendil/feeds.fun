import * as _ from "lodash";
import axios from "axios";
import * as t from "@/logic/types";

const ENTRY_POINT = 'http://127.0.0.1:8000'

const API_GET_FEEDS = `${ENTRY_POINT}/api/get-feeds`;
const API_GET_LAST_ENTRIES = `${ENTRY_POINT}/api/get-last-entries`;
const API_GET_ENTRIES_BY_IDS = `${ENTRY_POINT}/api/get-entries-by-ids`;


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
