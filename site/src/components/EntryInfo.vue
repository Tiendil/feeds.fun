<template>
<div>
  <a :href="entry.url" target="_blank" rel="noopener noreferrer">
    {{ entry.title }}
  </a>
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

const props = defineProps<{ entry: t.EntryInfo }>();


</script>

<style scoped>
</style>
