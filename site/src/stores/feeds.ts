import {computed, ref, watch} from "vue";
import {useRouter} from "vue-router";
import {defineStore} from "pinia";

import type * as t from "@/logic/types";
import * as e from "@/logic/enums";
import * as api from "@/logic/api";
import {Timer} from "@/logic/timer";
import {computedAsync} from "@vueuse/core";
import {useGlobalSettingsStore} from "@/stores/globalSettings";

export const useFeedsStore = defineStore("feedsStore", () => {
  const globalSettings = useGlobalSettingsStore();

  const feeds = computedAsync(async () => {
    // force refresh
    globalSettings.dataVersion;

    const feedsList = await api.getFeeds();

    const feedsDict: {[key: t.FeedId]: t.Feed} = {};

    for (const feed of feedsList) {
      feedsDict[feed.id] = feed;
    }

    return feedsDict;
  }, {});

  async function unsubscribe(feedId: t.FeedId) {
    await api.unsubscribe({feedId: feedId});
    globalSettings.updateDataVersion();
  }

  async function subscribe(url: t.URL) {
    await api.addFeed({
      url: url
    });

    globalSettings.updateDataVersion();
  }

  return {
    feeds,
    unsubscribe,
    subscribe
  };
});
