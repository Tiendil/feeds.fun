<template>
    <github-button
      class="mx-1"
      :href="repository"
      data-icon="octicon-star"
      >Star</github-button
    >

    <github-button
      class="mx-1"
      :href="repository + '/discussions'"
      data-show-count="true"
      data-icon="octicon-comment-discussion"
      >Discuss</github-button
    >
</template>

<script lang="ts" setup>
  const props = defineProps<{repository: string}>();
</script>

<style></style>
