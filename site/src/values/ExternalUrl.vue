<template>
  <a
    :href="url"
    target="_blank"
    rel="noopener noreferrer">
    {{ renderedText }}
    <i class="ti ti-external-link" />
  </a>
</template>

<script lang="ts" setup>
  import {computed} from "vue";
  import type * as t from "@/logic/types";

  const properties = defineProps<{url: t.URL; text?: string | null}>();

  const renderedText = computed(() => {
    if (properties.text) {
      return properties.text;
    }

    return properties.url;
  });
</script>

<style></style>
