<template>

  <table>
    <thead>
      <tr>
        <th>score</th>
        <th>title</th>
        <th>tags</th>
        <th>published at</th>
        <th>cataloged At</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="entry in entries" :key="entry.id">
        <td><value-score :value="entry.score"/></td>
        <td><value-url :value="entry.url" :text="entry.title"/></td>
        <td><tags-list :tags="entry.tags"/></td>
        <td><value-date-time :value="entry.publishedAt"/></td>
        <td><value-date-time :value="entry.catalogedAt"/></td>
      </tr>
    </tbody>
  </table>

</template>

<script lang="ts" setup>
import { computed } from "vue";
import * as t from "@/logic/types";

defineProps<{ entries: Array[t.Entry]}>();

</script>

<style></style>
