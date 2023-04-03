<template>
    <feeds-list :feeds="feeds" />
</template>

<script lang="ts" setup>
import { computed, ref, onUnmounted, watch } from "vue";
import { computedAsync } from "@vueuse/core";
import * as api from "@/logic/api";
import * as t from "@/logic/types";

const feeds = computedAsync(async () => {
    return await api.getFeeds();
}, null);

</script>

<style></style>
