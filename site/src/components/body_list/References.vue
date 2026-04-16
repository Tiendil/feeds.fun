<template>
  <div class="flex flex-wrap gap-2">
    <body-list-reference
      v-for="reference in references"
      :key="reference.url"
      :reference="reference" />
  </div>
</template>

<script lang="ts" setup>
  import type * as t from "@/logic/types";

  defineProps<{
    references: t.Reference[];
  }>();
</script>
