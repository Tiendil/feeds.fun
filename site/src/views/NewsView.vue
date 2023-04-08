<template>
    <entries-list :entries="entries" />
</template>

<script lang="ts" setup>
import { computed, ref, onUnmounted, watch } from "vue";
import { computedAsync } from "@vueuse/core";
import * as api from "@/logic/api";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";
import { useGlobalSettingsStore } from "@/stores/globalSettings";

const globalSettings = useGlobalSettingsStore();

const entries = computedAsync(async () => {
    return await api.getEntries({period: e.LastEntriesPeriodProperties.get(globalSettings.lastEntriesPeriod).seconds});
}, null);

</script>

<style></style>
