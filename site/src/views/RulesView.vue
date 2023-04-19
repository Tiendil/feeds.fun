<template>
    <rules-list :rules="rules" />
</template>

<script lang="ts" setup>
import { computed, ref, onUnmounted, watch } from "vue";
import { computedAsync } from "@vueuse/core";
import * as api from "@/logic/api";
import * as t from "@/logic/types";

const rules = computedAsync(async () => {
    return await api.getRules();
}, null);

</script>

<style></style>
