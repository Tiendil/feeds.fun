<template>
  <span>{{ text }}</span>
</template>

<script lang="ts" setup>
  import {computed} from "vue";
  import * as u from "@/logic/utils";

  const properties = defineProps<{
    value: Date | null;
    reversed?: boolean;
  }>();

  const text = computed(() => {
    if (properties.value === null) {
      return "—";
    }

    if (properties.reversed) {
      return u.timeSince(properties.value);
    }

    return properties.value.toLocaleString();
  });
</script>

<style></style>
