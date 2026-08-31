<template>
  <app-tooltip placement="top-end">
    <span
      :class="[
        'block cursor-help focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500',
        variant === 'column'
          ? 'w-16 flex-shrink-0 rounded-sm text-right'
          : 'rounded border bg-white px-1 py-1 text-sm font-medium leading-tight text-gray-900'
      ]"
      tabindex="0">
      {{ displayedTime }}
    </span>

    <template #content>
      <div><span class="font-medium">Considered published at:</span> {{ formatDate(effectivePublishedAt) }}</div>
      <div><span class="font-medium">First seen by Feeds Fun:</span> {{ formatDate(firstSeenAt) }}</div>
      <div><span class="font-medium">Published by the source:</span> {{ formatDate(sourcePublishedAt) }}</div>
    </template>
  </app-tooltip>
</template>

<script lang="ts" setup>
  import {computed} from "vue";
  import * as utils from "@/logic/utils";

  type EntryDateVariant = "column" | "metadata";

  const properties = defineProps<{
    effectivePublishedAt: Date;
    firstSeenAt: Date;
    sourcePublishedAt: Date;
    variant: EntryDateVariant;
  }>();

  const displayedTime = computed(() => {
    const style = properties.variant === "column" ? "short" : "long";
    return utils.timeSince(properties.effectivePublishedAt, style);
  });

  function formatDate(date: Date): string {
    return date.toLocaleString();
  }
</script>
