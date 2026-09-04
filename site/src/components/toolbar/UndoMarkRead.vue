<template>
  <ui-button
    variant="tonal"
    size="compact"
    tooltip='Undo last "mark read" operation'
    :disabled="!entriesStore.canUndoMarkRead"
    @click="entriesStore.undoMarkRead()">
    <icon
      icon="undo"
      size="small" />
  </ui-button>
</template>

<script lang="ts" setup>
  import {useEntriesStore} from "@/stores/entries";

  const entriesStore = useEntriesStore();
</script>
