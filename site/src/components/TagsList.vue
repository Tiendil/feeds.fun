<template>

  <ul style="list-style-type: none; margin: 0; padding: 0">
    <li v-for="tag of tags" style="display: inline">
      {{tag}}&nbsp;
    </li>
  </ul>

</template>

<script lang="ts" setup>

defineProps<{ tags: string[]}>();

</script>

<style></style>
