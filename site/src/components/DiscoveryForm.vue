<template>
  <div>
    <form @submit.prevent="searhedUrl = search">
      <input
        type="text"
        class="ffun-input mr-1"
        v-model="search"
        :disabled="disableInputs"
        placeholder="Enter a site URL" />

      <button
        type="submit"
        class="ffun-form-button"
        :disabled="disableInputs">
        Search
      </button>
    </form>

    <p
      v-if="searching"
      class="ffun-info-waiting mt-2"
      >Searching for feeds…</p
    >

    <div v-else-if="foundFeeds === null"></div>

    <div
      v-else-if="foundFeeds.length === 0"
      class="ffun-info-bad mt-2">
      <p v-for="message in messages">
        {{ message.message }}
      </p>

      <p v-if="messages.length === 0"> No feeds found. </p>
    </div>

    <div
      v-for="feed in foundFeeds"
      :key="feed.url">
      <feed-info :feed="feed" />

      <p
        v-if="feed.isLinked"
        class="ffun-info-good">
        You are already subscribed to this feed.
      </p>

      <template v-else>
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
      </template>
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
  import {useFeedsStore} from "@/stores/feeds";

  const feedsStore = useFeedsStore();

  const search = ref("");

  const searching = ref(false);
  const adding = ref(false);

  const disableInputs = computed(() => searching.value || adding.value);

  const searhedUrl = ref("");

  const addedFeeds = ref<{[key: string]: boolean}>({});

  let messages = ref<t.ApiMessage[]>([]);

  const foundFeeds = computedAsync(async () => {
    if (searhedUrl.value === "") {
      return null;
    }

    searching.value = true;
    messages.value = [];

    let feeds: t.FeedInfo[] = [];

    try {
      const answer = await api.discoverFeeds({url: searhedUrl.value});
      feeds = answer.feeds;
      messages.value = answer.messages;
    } catch (e) {
      console.error(e);
    }

    searching.value = false;

    return feeds;
  }, null);

  async function addFeed(url: t.URL) {
    adding.value = true;

    await feedsStore.subscribe(url);

    addedFeeds.value[url] = true;

    adding.value = false;
  }
</script>

<style scoped></style>
