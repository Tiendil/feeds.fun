<template>
<side-panel-layout :reload-button="false">
  <template #main-header> Settings </template>

    <ul>
      <li>
        <strong class="mr-1">User id</strong>
        <input
          class="ffun-input w-72"
          disabled
          :value="userId"/>
      </li>
    </ul>

    <hr/>

    <template v-for="(value, kind) of globalSettings.userSettings">
      <user-setting :kind="kind" />
      <hr/>
    </template>

    <h2>OpenAI usage</h2>

    <p>Token usage for your OpenAI key per month.</p>

    <ul>
      <li> <strong>Used tokens</strong>: the number of tokens in processed requests. </li>
      <li>
        <strong>Reserved tokens</strong>: the number of tokens reserved for requests that currently are processing or
        were not processed correctly.
      </li>
      <li>
        <strong>Total tokens</strong>: the total number of tokens used in the month. Should be not less than the actual
        used tokens, but can be bigger because we reserve more tokens than actually use.
      </li>
    </ul>

    <p v-if="openAIUsage == null">Loading...</p>

    <p v-else-if="openAIUsage.length == 0">No usage data</p>

    <table v-else>
      <thead>
        <tr>
          <th style="padding-left: 1rem">Period</th>
          <th style="padding-left: 1rem">Used tokens</th>
          <th style="padding-left: 1rem">Reserved tokens</th>
          <th style="padding-left: 1rem">Total tokens</th>
          <th style="padding-left: 1rem">% from current maximum</th>
        </tr>
      </thead>
      <tbody>
        <openai-tokens-usage
          :usage="usage"
          v-for="usage of openAIUsage" />
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

  const openAIUsage = computedAsync(async () => {
    return await api.getResourceHistory({kind: "openai_tokens"});
  }, null);

  const userId = computed(() => {
    if (globalSettings.info == null) {
      return "—";
    }

    return globalSettings.info.userId;
  });
</script>

<style></style>
