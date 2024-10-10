<template>
  <side-panel-layout :reload-button="false">
    <template #main-header> Settings </template>

    <ul>
      <li>
        <strong class="mr-1">User id</strong>
        <input
          class="ffun-input w-72"
          disabled
          :value="userId" />
      </li>
    </ul>

    <hr />

    <template v-for="kind of settingsOrder">
      <user-setting :kind="kind" />
      <hr />
    </template>

    <h3>API usage</h3>

    <p>Estimated tokens cost for your API keys usage per month.</p>

    <ul class="list-disc list-inside">
      <li> <strong>Estimated Used USD</strong> — the estimated cost of tokens in processed requests. </li>
      <li>
        <strong>Estimated Reserved USD</strong> — the estimated cost of tokens reserved for requests that currently are
        processing or were not processed correctly.
      </li>
      <li> <strong>Estimated Total USD</strong> — the estimated total cost of tokens used in the month. </li>
    </ul>

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

  // TODO: refactor, this is the temporary code to display settings in the right order
  const settingsOrder = [
    "openai_api_key",
    "gemini_api_key",
    "max_tokens_cost_in_month",
    "process_entries_not_older_than",
    "hide_message_about_setting_up_key",
    "hide_message_about_adding_collections",
    "hide_message_check_your_feed_urls"
  ];
</script>

<style></style>
