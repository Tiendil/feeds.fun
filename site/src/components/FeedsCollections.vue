<template>
<div>
  <select multiple>
    <option v-for="item in collections" :key="item" :value="item">
            value="item">{{item}}</option>
  </select>
</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";
import * as api from "@/logic/api";
import { computedAsync } from "@vueuse/core";
import DOMPurify from "dompurify";
import { useEntriesStore } from "@/stores/entries";


const collections = computedAsync(async () => {
    return await api.getFeedsCollections();
});


</script>

<style scoped>
</style>
