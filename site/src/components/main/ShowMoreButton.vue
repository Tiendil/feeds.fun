<template>
  <button
    class="ffun-main-button short"
    @click="emit('update:expanded', !properties.expanded)">
    {{ properties.expanded ? "Show less" : "Show more" }}
  </button>
</template>

<script lang="ts" setup>
  const properties = defineProps<{
    expanded: boolean;
  }>();

  const emit = defineEmits<{
    "update:expanded": [value: boolean];
  }>();
</script>
