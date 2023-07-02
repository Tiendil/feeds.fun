<template>
<side-panel-layout :reload-button="false">

  <template #main-header>
    Settings
  </template>

  <user-setting v-for="(value, kind) of globalSettings.userSettings"
                :kind="kind"/>

  <h2>OpenAI usage</h2>

  <p>Token usage for your OpenAI key per month.</p>

  <ul>
    <li><strong>Used tokens</strong>: the number of tokens used in success requests.</li>
    <li><strong>Reserved tokens</strong>: the number of tokens reserved for requests that were not processed correctly.</li>
    <li><strong>Total tokens</strong>: the total number of tokens used in the month. Should be not less than the actual used tokens, but can be bigger because we reserve more tokens than actually use.</li>
  </ul>

  <p v-if="openAIUsage == null">Loading...</p>

  <p v-else-if="openAIUsage.length == 0">No usage data</p>

  <table v-else>
    <thead>
      <tr>
        <th style="padding-left: 1rem;">Period</th>
        <th style="padding-left: 1rem;">Used tokens</th>
        <th style="padding-left: 1rem;">Reserved tokens</th>
        <th style="padding-left: 1rem;">Total tokens</th>
        <th style="padding-left: 1rem;">% from current maximum</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="usage of openAIUsage">
        <td>{{ renderPeriod(usage.intervalStartedAt)}}</td>
        <td style="text-align: right;">{{ usage.used }}</td>
        <td style="text-align: right;">{{ usage.reserved }}</td>
        <td style="text-align: right;">{{ usage.total() }}</td>
        <td style="text-align: right;">{{ raughPercents(usage.total()) }}%</td>
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


function renderPeriod(date: Date) {
    return date.toLocaleString("default", { month: "long",
                                            year: "numeric"});
}

function raughPercents(total: number) {
    const setting = globalSettings.userSettings['openai_max_tokens_in_month'];

    if (!setting) {
        return '—';
    }

    const limit = setting.value;

    if (limit == 0) {
        return '—';
    }

    return (total / limit * 100).toFixed(5);
}

</script>

<style></style>
