import {ref} from "vue";
import {defineStore} from "pinia";

import * as t from "@/logic/types";
import * as api from "@/logic/api";
import {Timer} from "@/logic/timer";
import {computedAsync} from "@vueuse/core";
import {useGlobalSettingsStore} from "@/stores/globalSettings";

export const useFeedsStore = defineStore("feedsStore", () => {
  const globalSettings = useGlobalSettingsStore();

  const feeds = ref<{[key: t.FeedId]: t.Feed}>({});
  const requestedFeeds = ref<{[key: t.FeedId]: boolean}>({});
  const displayedFeedId = ref<t.FeedId | null>(null);

  function feedWithFullDataFromStorage(feed: t.Feed, preserveFullData: boolean) {
    // Full feed details power derived UI, like activity charts. On full list
    // refresh we must drop them so opened feed bodies reload fresh details.
    if (!preserveFullData) {
      return feed;
    }

    if (feed.id in feeds.value) {
      const existingFeed = feeds.value[feed.id];

      if (feed.entriesLoadedDetails === null && existingFeed.entriesLoadedDetails !== null) {
        return {
          ...feed,
          entriesLoadedDetails: existingFeed.entriesLoadedDetails
        };
      }
    }

    return feed;
  }

  function registerFeeds({newFeeds, replace}: {newFeeds: t.Feed[]; replace: boolean}) {
    const delta: {[key: t.FeedId]: t.Feed} = {};

    for (const feed of newFeeds) {
      delta[feed.id] = feedWithFullDataFromStorage(feed, !replace);
    }

    if (replace) {
      feeds.value = delta;

      if (displayedFeedId.value === null) {
        return;
      }

      if (!(displayedFeedId.value in feeds.value)) {
        displayedFeedId.value = null;
        return;
      }

      requestFullFeed({feedId: displayedFeedId.value});

      return;
    }

    feeds.value = {...feeds.value, ...delta};
  }

  const loadedFeedsReport = computedAsync(async () => {
    // force refresh
    globalSettings.dataVersion;

    const feedsList = await api.getFeeds();

    registerFeeds({
      newFeeds: feedsList,
      replace: true
    });

    return feedsList.map((feed) => feed.id);
  }, null);

  function requestFullFeed({feedId}: {feedId: t.FeedId}) {
    if (feedId in feeds.value && feeds.value[feedId].entriesLoadedDetails !== null) {
      return;
    }

    requestedFeeds.value[feedId] = true;
  }

  function displayFeed({feedId}: {feedId: t.FeedId}) {
    displayedFeedId.value = feedId;

    requestFullFeed({feedId: feedId});
  }

  function hideFeed({feedId}: {feedId: t.FeedId}) {
    if (displayedFeedId.value === feedId) {
      displayedFeedId.value = null;
    }
  }

  async function loadFullFeeds() {
    const ids: t.FeedId[] = Object.keys(requestedFeeds.value).map((key) => t.toFeedId(key));

    if (ids.length === 0) {
      return;
    }

    const loadedFeeds = await api.getFeedsByIds({ids: ids});

    registerFeeds({
      newFeeds: loadedFeeds,
      replace: false
    });

    requestedFeeds.value = {};
  }

  const requestedFeedsTimer = new Timer(loadFullFeeds, 1000);

  requestedFeedsTimer.start();

  async function unsubscribe(feedId: t.FeedId) {
    await api.unsubscribe({feedId: feedId});

    // Attention, do not update globalSettings.updateDataVersion here
    // it cause a lot of unnecessary requests to the server without any benefit
    // we just remove feed from frontend

    const updatedFeeds = {...feeds.value};
    delete updatedFeeds[feedId];
    feeds.value = updatedFeeds;
  }

  async function subscribe(url: t.URL) {
    const newFeed = await api.addFeed({
      url: url
    });

    // Attention, do not update globalSettings.updateDataVersion here (see above)

    registerFeeds({
      newFeeds: [newFeed],
      replace: false
    });
  }

  return {
    feeds,
    loadedFeedsReport,
    displayedFeedId,
    requestFullFeed,
    displayFeed,
    hideFeed,
    unsubscribe,
    subscribe
  };
});
