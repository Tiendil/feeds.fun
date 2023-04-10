<template>

  <table>
    <thead>
      <tr>
        <th>id</th>
        <th>state</th>
        <th>url</th>
        <th>loaded at</th>
      </tr>
    </thead>
    <tbody>
      <tr v-for="feed in feeds">
        <td><value-feed-id :value="feed.id"/></td>
        <td>{{feedState(feed)}}</td>
        <td><value-url :value="feed.url"/></td>
        <td>
          <value-date-time v-if="feed.loadedAt !== null" :value="feed.loadedAt"/>
          <span v-else>—</span>
        </td>
      </tr>
    </tbody>
  </table>

</template>

<script lang="ts" setup>
import * as t from "@/logic/types";

defineProps<{ feeds: Array[t.Feed]}>();

function feedState(feed: t.Feed) {
    if (feed.state === "not_loaded") {
        return "loading";
    } else if (feed.state === "loaded") {
        return "loaded";
    } else if (feed.state === "damaged") {
        return feed.lastError;
    } else {
        return "unknown";
    }
}

</script>

<style></style>
