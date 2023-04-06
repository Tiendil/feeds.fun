<template>
    <entries-list :entries="entries" />
</template>

<script lang="ts" setup>
import { computed, ref, onUnmounted, watch } from "vue";
import { computedAsync } from "@vueuse/core";
import * as api from "@/logic/api";
import * as t from "@/logic/types";

const entries = computedAsync(async () => {
    return await api.getEntries();
}, null);

</script>

<style></style>
