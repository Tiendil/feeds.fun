<template>
  <div>
    <input
      type="text"
      class="ffun-input mr-1"
      v-model="search"
      :disabled="loading"
      placeholder="Search for feeds" />

    <button
      class="ffun-form-button"
      :disabled="loading"
      @click.prevent="searhedUrl = search">
      Search
    </button>

    <hr />

    <div v-if="!loading && foundFeeds.length === 0">No feeds found</div>

    <div v-else-if="loading">Searching for feeds…</div>

    <div v-else>
      <div
        v-for="feed in foundFeeds"
        :key="feed.url">
        <feed-info :feed="feed" />

        <button
          class="ffun-form-button"
          v-if="!addedFeeds[feed.url]"
          @click.prevent="addFeed(feed.url)">
          Add
        </button>

        <p
          v-else
          class="ffun-info-good"
          >Feed added</p
        >
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import {useEntriesStore} from "@/stores/entries";

  const search = ref("");
  const loading = ref(false);

  const searhedUrl = ref("");

  const addedFeeds = ref<{[key: string]: boolean}>({});

  const foundFeeds = computedAsync(async () => {
    if (searhedUrl.value === "") {
      return [];
    }

    loading.value = true;

    let feeds: t.FeedInfo[] = [];

    try {
      feeds = await api.discoverFeeds({url: searhedUrl.value});
    } catch (e) {
      console.error(e);
    }

    loading.value = false;

    return feeds;
  }, []);

  async function addFeed(url: string) {
    addedFeeds.value[url] = true;

    await api.addFeed({url: url});
  }
</script>

<style scoped></style>
