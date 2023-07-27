<template>
  <side-panel-layout :reload-button="false">
    <template #main-header>
      Rules
      <span v-if="rules">[{{ rules.length }}]</span>
    </template>

    <rules-list :rules="rules" />
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch} from "vue";
  import {computedAsync} from "@vueuse/core";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import * as api from "@/logic/api";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";

  const globalSettings = useGlobalSettingsStore();

  globalSettings.mainPanelMode = e.MainPanelMode.Rules;

  const rules = computedAsync(async () => {
    // force refresh
    globalSettings.dataVersion;
    return await api.getRules();
  }, null);
</script>

<style></style>
