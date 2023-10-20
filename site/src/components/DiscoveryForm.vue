<template>
<div>
  <form @submit.prevent="searhedUrl = search">
    <input
      type="text"
      class="ffun-input mr-1"
      v-model="search"
      :disabled="disableInputs"
      placeholder="Search for feeds" />

    <button
      type="submit"
      class="ffun-form-button"
      :disabled="disableInputs">
      Search
    </button>
  </form>

    <p v-if="searching" class="ffun-info-attention">Searching for feeds…</p>

    <p v-else-if="foundFeeds === null" class="ffun-info-attention">Enter a URL to search for feeds.</p>

    <p v-else-if="foundFeeds.length === 0" class="ffun-info-attention">No feeds found.</p>

    <div
      v-for="feed in foundFeeds"
      :key="feed.url">
      <feed-info :feed="feed" />

      <button
        class="ffun-form-button"
        v-if="!addedFeeds[feed.url]"
        :disabled="disableInputs"
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
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import {useEntriesStore} from "@/stores/entries";

const search = ref("");

const searching = ref(false);
const adding = ref(false);

const disableInputs = computed(() => searching.value || adding.value);

  const searhedUrl = ref("");

  const addedFeeds = ref<{[key: string]: boolean}>({});

  const foundFeeds = computedAsync(async () => {
    if (searhedUrl.value === "") {
      return null;
    }

    searching.value = true;

    let feeds: t.FeedInfo[] = [];

    try {
      feeds = await api.discoverFeeds({url: searhedUrl.value});
    } catch (e) {
      console.error(e);
    }

    searching.value = false;

    return feeds;
  }, null);

  async function addFeed(url: string) {

    adding.value = true;

    await api.addFeed({url: url});

    addedFeeds.value[url] = true;

    adding.value = false;
  }
</script>

<style scoped></style>
