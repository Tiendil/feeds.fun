<template>
    <h2>
      Rules
      <span v-if="rules">[{{rules.length}}]</span>
    </h2>

    <rules-list :rules="rules" />
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