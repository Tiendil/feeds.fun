<template>
  <a :href="value" target="_blank">{{value}}</a>
</template>

<script lang="ts" setup>
  import * as t from "@/logic/types";

  defineProps<{ value: t.URL }>();

</script>

<style></style>
