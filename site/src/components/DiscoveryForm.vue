<template>
  <div>
    <form
      class="ui-form-row"
      @submit.prevent="searhedUrl = search">
      <input
        type="text"
        class="ffun-input ui-form-row-control"
        v-model="search"
        :disabled="disableInputs"
        placeholder="Enter a site URL" />

      <ui-button
        variant="primary"
        type="submit"
        :disabled="disableInputs">
        Search
      </ui-button>
    </form>

    <ui-notice
      v-if="searching"
      tone="info"
      class="mt-2"
      >Searching for feeds…</ui-notice
    >

    <div v-else-if="foundFeeds === null"></div>

    <ui-notice
      v-else-if="foundFeeds.length === 0"
      tone="danger"
      class="mt-2">
      <p v-for="message in messages">
        {{ message.message }}
      </p>

      <p v-if="messages.length === 0"> No feeds found. </p>
    </ui-notice>

    <div
      v-for="feed in foundFeeds"
      :key="feed.url">
      <feed-info :feed="feed" />

      <ui-notice
        v-if="feed.isLinked"
        tone="success">
        You are already subscribed to this feed.
      </ui-notice>

      <template v-else>
        <ui-button
          variant="primary"
          v-if="!addedFeeds[feed.url]"
          :disabled="disableInputs"
          @click.prevent="addFeed(feed.url)">
          Add
        </ui-button>

        <ui-notice
          v-else
          tone="success"
          >Feed added</ui-notice
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
