<template>

  <table>
    <thead>
      <tr>
        <th>id</th>
        <th>url</th>
        <th>loaded at</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="feed in feeds">
        <td><value-feed-id :value="feed.id"/></td>
        <td><value-url :value="feed.url"/></td>
        <td><value-date-time :value="feed.loadedAt"/></td>
      </tr>
    </tbody>
  </table>

</template>

<script lang="ts" setup>

import * as t from "@/logic/types";

defineProps<{ feeds: Array[t.Feed]}>();

</script>

<style></style>
