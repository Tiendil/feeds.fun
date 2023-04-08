<template>

  <table>
    <thead>
      <tr>
        <th>score</th>
        <th>title</th>
        <th>tags</th>
        <th>time</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="entry in entries" :key="entry.id">
        <td><value-score :value="entry.score"/></td>
        <td><value-url :value="entry.url" :text="entry.title"/></td>
        <td><tags-list :tags="entry.tags"/></td>
        <td><value-date-time :value="timeFor(entry)" :reversed="true"/></td>
      </tr>
    </tbody>
  </table>

</template>

<script lang="ts" setup>
import { computed } from "vue";
import * as t from "@/logic/types";

const properties = defineProps<{ entries: Array[t.Entry],
                                 timeField: string}>();


function timeFor(entry: t.Entry): Date {
  return entry[properties.timeField];
}

</script>

<style></style>
