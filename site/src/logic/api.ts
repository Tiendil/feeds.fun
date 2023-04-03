import * as _ from "lodash";
import axios from "axios";
import * as t from "@/logic/types";

const ENTRY_POINT = 'http://127.0.0.1:8000'

const API_GET_FEEDS = `${ENTRY_POINT}/api/get-feeds`;


export async function getFeeds() {

    try {
        const response = await axios.post(API_GET_FEEDS, {});

        const feeds = [];

        for (let rawFeed of response.data.feeds) {
            const feed = t.feedFromJSON(rawFeed);
            feeds.push(feed);
        }

        return feeds;
    } catch (error) {
        console.log(error);
        throw error;
    }
}
