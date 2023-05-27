<template>
<side-panel-layout>
  <template #main-header>
    <h2 style="margin-top: 0;">
      Rules
      <span v-if="rules">[{{rules.length}}]</span>
    </h2>
  </template>

  <template #main-footer>
  </template>

  <rules-list :rules="rules" />
</side-panel-layout>
</template>

<script lang="ts" setup>
import { computed, ref, onUnmounted, watch } from "vue";
import { computedAsync } from "@vueuse/core";
import { useGlobalSettingsStore } from "@/stores/globalSettings";
import * as api from "@/logic/api";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";

const globalSettings = useGlobalSettingsStore();

globalSettings.mainPanelMode = e.MainPanelMode.Rules;

const rules = computedAsync(async () => {
    return await api.getRules({dataVersion: globalSettings.dataVersion});
}, null);

</script>

<style></style>
