<template>
  <ul style="list-style-type: none; margin: 0; padding: 0">
    <li v-for="(feed, index) in feeds">
      {{index}} - {{feed}}
    </li>
  </ul>
</template>

<script lang="ts" setup>

import * as t from "@/logic/types";

defineProps<{ feeds: Array[t.Feed]}>();

</script>

<style></style>
