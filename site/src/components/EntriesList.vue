<template>

  <table>
    <thead>
      <tr>
        <th>title</th>
        <th>tags</th>
        <th>published at</th>
        <th>cataloged At</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="entry in entries">
        <td><value-url :value="entry.url" :text="entry.title"/></td>
        <td>{{entry.tags}}</td>
        <td><value-date-time :value="entry.publishedAt"/></td>
        <td><value-date-time :value="entry.catalogedAt"/></td>
      </tr>
    </tbody>
  </table>

</template>

<script lang="ts" setup>

import * as t from "@/logic/types";

defineProps<{ entries: Array[t.Entry]}>();

</script>

<style></style>
