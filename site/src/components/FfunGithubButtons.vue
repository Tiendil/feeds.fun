<template>
  <github-button :href="repository" data-show-count="true" data-icon="octicon-star">Star</github-button>
  &nbsp;
  <github-button :href="repository + '/discussions'" data-show-count="true" data-icon="octicon-comment-discussion">Discuss</github-button>
</template>

<script lang="ts" setup>

const props = defineProps<{ repository: string }>();

</script>

<style></style>
