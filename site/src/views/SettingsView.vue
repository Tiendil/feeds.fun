<template>
  <side-panel-layout :reload-button="false">
    <template #main-header> Settings </template>

    <h3>General</h3>

    <label class="mr-1">User id</label>
    <input
      class="ffun-input w-72 cursor-pointer"
      disabled
      :value="userId" />

    <h3>Messages</h3>

    <user-setting
      v-for="kind of messagesSettings"
      key="kind"
      :kind="kind" />

    <h3>Tagging</h3>

    <div class="ffun-info-common">
      <p>
        All feeds from
        <a
          href="#"
          @click.prevent="goToCollections()"
          >collections</a
        >
        are tagged for free.
      </p>

      <p>
        If you want to tag your own feeds, we kindly ask you to provide an
        <external-url
          url="https://platform.openai.com/docs/api-reference/introduction"
          text="OpenAI" />
        or
        <external-url
          url="https://ai.google.dev/gemini-api/docs/api-key"
          text="Gemini" />
        API key.
      </p>

      <p><strong>Here is how we use your API key:</strong></p>

      <ul>
        <li>We use your key only for your feeds that are not part of predefined collections.</li>
        <li>We stop using your key when its usage exceeds the monthly limit you set.</li>
        <li
          >If a feed has multiple subscribers with API keys, we'll use a key with the lowest usage in the current
          month.</li
        >
        <li>We do not process old news until you tell us to.</li>
      </ul>

      <p><strong>The more users set up an API key, the cheaper Feeds Fun becomes for everyone.</strong></p>

      <p>API key usage statistics are available on this page.</p>
    </div>

    <user-setting
      kind="openai_api_key"
      class="mt-4" />
    <user-setting kind="gemini_api_key" />
    <user-setting kind="max_tokens_cost_in_month" />

    <user-setting kind="process_entries_not_older_than" />

    <div class="ffun-info-common mb-4">
      <p>
        The age of a news item is calculated based on the time it was published (according to the data in the feed).
      </p>
    </div>

    <h3>API usage</h3>

    <div class="ffun-info-common mb-4">
      <p>Estimated tokens cost for your API keys usage per month.</p>

      <ul class="list-disc list-inside">
        <li> <strong>Estimated Used USD</strong> — the estimated cost of tokens in processed requests. </li>
        <li>
          <strong>Estimated Reserved USD</strong> — the estimated cost of tokens reserved for requests that are
          currently processing or were not processed correctly.
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

    <h3>Danger Zone</h3>

    <div class="ffun-info-bad">
      <p><strong>ATTENTION!</strong></p>

      <p> Operations in this section are irreversible and may lead to data loss and even account deletion. </p>
    </div>

    <div
      v-if="!globalState.isSingleUserMode"
      class="ffun-info-bad">
      <button
        @click.prevent="removeAccount()"
        class="ffun-form-button bad short pl-0"
        >Remove Account</button
      >

      <label class="ml-1"> Permanently remove your account and all your data. </label>
    </div>

    <div
      v-else
      class="ffun-info-common">
      <p> Account removal in the single-user mode is not available. </p>
    </div>
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch, provide} from "vue";
  import {computedAsync} from "@vueuse/core";
  import * as api from "@/logic/api";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as settings from "@/logic/settings";
  import {useRouter} from "vue-router";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useGlobalState} from "@/stores/globalState";

  const globalState = useGlobalState();
  const globalSettings = useGlobalSettingsStore();

  provide("eventsViewName", "settings");

  globalSettings.mainPanelMode = e.MainPanelMode.Settings;

  const tokensCostData = computedAsync(async () => {
    return await api.getResourceHistory({kind: "tokens_cost"});
  }, null);

  const userId = computed(() => {
    return globalState.userId == null ? "—" : globalState.userId;
  });

  const messagesSettings = [
    "hide_message_about_setting_up_key",
    "hide_message_about_adding_collections",
    "hide_message_check_your_feed_urls"
  ];

  const router = useRouter();

  function goToCollections() {
    router.push({name: e.MainPanelMode.Collections, params: {}});
  }

  function removeAccount() {
    if (confirm("Are you sure you want to remove your account? THIS OPERATION IS NOT REVERSIBLE!")) {
      api.removeUser();
    }
  }

  // TODO: check api keys on setup
  // TODO: basic integer checks
</script>
