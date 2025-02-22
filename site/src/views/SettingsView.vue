<template>
  <side-panel-layout :reload-button="false">
    <template #main-header> Settings </template>

    <h3>General</h3>

    <div class="ffun-info-common mb-4">
      <p>
        User id is used to identify you in the system. Please provide it when you search for help or report a bug.
      </p>
    </div>

    <label class="mr-1">User id</label>
    <input
      class="ffun-input w-72 cursor-pointer"
      disabled
      :value="userId" />

    <h3>Messages</h3>

    <user-setting v-for="kind of messagesSettings"
                  key="kind"
                  :kind="kind"/>

    <h3>Artificial Intelligence & tagging</h3>

    <div class="ffun-info-common">
      <p>
        All feeds from
        <a class="ffun-normal-link" href="#" @click.prevent="goToCollections()">collections</a>
        are tagged for free.
      </p>

      <p>
        If you want to tag your own feeds, we kindly ask you to provide an
        <a href="">OpenAI</a> or/and Gemini API key.
      </p>

      <p><strong>Here's how your API key will be used:</strong></p>

      <ul>
        <li>We use your key only for your feeds, that are not part of predefined collections.</li>
        <li>We track your key usage and stop using it if it exceed your monthly limit.</li>
        <li>If a feed has multiple subscribers with API keys, we'll use a key with the lowest usage in the current month.</li>
        <li>We limit the age of news to be processed with your API key, to safe your resources.</li>
      </ul>

      <p><strong>The more users set up an API key, the cheaper Feeds Fun becomes for everyone.</strong></p>

      <p>API key usage statistics is available on this page.</p>
    </div>

    <user-setting kind="openai_api_key" class="mt-4"/>
    <user-setting kind="gemini_api_key"/>
    <user-setting kind="max_tokens_cost_in_month"/>

    <div class="ffun-info-common mb-4">
      <p>
        The age of a news item is calculated based on the time it was published (according to the data in the feed).
      </p>
    </div>

    <user-setting kind="process_entries_not_older_than"/>

    <h3>API usage</h3>

    <div class="ffun-info-common mb-4">
    <p>Estimated tokens cost for your API keys usage per month.</p>

    <ul class="list-disc list-inside">
      <li> <strong>Estimated Used USD</strong> — the estimated cost of tokens in processed requests. </li>
      <li>
        <strong>Estimated Reserved USD</strong> — the estimated cost of tokens reserved for requests that currently are
        processing or were not processed correctly.
      </li>
      <li> <strong>Estimated Total USD</strong> — the estimated total cost of tokens used in the month. </li>
    </ul>
    </div>

    <p v-if="tokensCostData == null">Loading...</p>

    <table
      v-else
      class="border border-gray-300 rounded-lg">
      <thead class="bg-slate-200">
        <tr>
          <th class="w-32">Period</th>
          <th class="w-48">Estimated Used USD </th>
          <th class="w-48">Estimated Reserved USD</th>
          <th class="w-48">Estimated Total USD</th>
          <th class="w-48">% From Maximum</th>
        </tr>
      </thead>
      <tbody>
        <tokens-cost
          :usage="usage"
          v-for="usage of tokensCostData" />

        <tr v-if="tokensCostData.length == 0">
          <td class="text-center">—</td>
          <td class="text-center">—</td>
          <td class="text-center">—</td>
          <td class="text-center">—</td>
          <td class="text-center">—</td>
        </tr>
      </tbody>
    </table>
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch} from "vue";
  import {computedAsync} from "@vueuse/core";
  import * as api from "@/logic/api";
  import * as t from "@/logic/types";
import * as e from "@/logic/enums";
  import {useRouter} from "vue-router";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

  const globalSettings = useGlobalSettingsStore();

  globalSettings.mainPanelMode = e.MainPanelMode.Settings;

  const tokensCostData = computedAsync(async () => {
    return await api.getResourceHistory({kind: "tokens_cost"});
  }, null);

  const userId = computed(() => {
    if (globalSettings.info == null) {
      return "—";
    }

    return globalSettings.info.userId;
  });

  const messagesSettings = [
    "hide_message_about_setting_up_key",
    "hide_message_about_adding_collections",
    "hide_message_check_your_feed_urls",
  ];

  const router = useRouter();

  function goToCollections() {
    router.push({name: e.MainPanelMode.Collections, params: {}});
  }

// TODO: check api keys on setup
// TODO: basic integer checks
</script>
