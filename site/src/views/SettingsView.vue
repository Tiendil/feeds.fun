<template>
<side-panel-layout :reload-button="false">

  <template #main-header>
    Settings
  </template>

  <user-setting v-for="(value, kind) of globalSettings.userSettings"
                :kind="kind"/>

  <h2>OpenAI usage</h2>

  <p v-if="openAIUsage == null">Loading...</p>

  <p v-else-if="openAIUsage.length == 0">No usage data</p>

  <table  v-else>
    <thead>
      <tr>
        <th>Period</th>
        <th>Used tokens</th>
        <th>Reserved tokens</th>
        <th>Total tokens</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="usage of openAIUsage">
        <td>{{ usage.intervalStartedAt }}</td>
        <td>{{ usage.used }}</td>
        <td>{{ usage.reserved }}</td>
        <td>{{ usage.total() }}</td>
      </tr>
    </tbody>
  </table>

</side-panel-layout>
</template>

<script lang="ts" setup>
import { computed, ref, onUnmounted, watch } from "vue";
import { computedAsync } from "@vueuse/core";
import * as api from "@/logic/api";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";
import { useGlobalSettingsStore } from "@/stores/globalSettings";

const globalSettings = useGlobalSettingsStore();

globalSettings.mainPanelMode = e.MainPanelMode.Settings;

const openAIUsage = computedAsync(async () => {
    return await api.getResourceHistory({kind: "openai_tokens"});
}, null);

</script>

<style></style>
