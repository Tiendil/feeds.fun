<template>

  <ul style="list-style-type: none; margin: 0; padding: 0;">
    <li v-for="entry in entries"
        :key="entry.id"
        style="margin-bottom: 0.25rem;">
      <entry-for-list :entry="entry"
                      :time-field="timeField"
                      :show-tags="showTags"/>
    </li>
  </ul>

</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import * as t from "@/logic/types";
import { computedAsync } from "@vueuse/core";

const properties = defineProps<{ entries: Array[t.Entry],
                                 timeField: string,
                                 showTags: boolean}>();

function timeFor(entry: t.Entry): Date {
  return entry[properties.timeField];
}

</script>

<style></style>
