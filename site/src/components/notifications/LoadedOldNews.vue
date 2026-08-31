<template>
  <!-- TODO: Hide when loading new news from the server -->
  <!-- Currently, after changing the period, this message does not disappear -->
  <!-- until the backend returns a new response -->
  <!-- It confuses users because the period size is changing in the text at the beginning of the request. -->
  <ui-notice
    v-if="showNotification"
    tone="info">
    <p> We have not found any news that is newer than {{ period.text }}, so we loaded some older ones. </p>
  </ui-notice>
</template>

<script lang="ts" setup>
  import {computed} from "vue";
  import * as e from "@/logic/enums";
  import type * as t from "@/logic/types";
  import {useEntriesStore} from "@/stores/entries";

  const entriesStore = useEntriesStore();

  const properties = defineProps<{
    entries: t.EntryId[];
    fallbackUsed: boolean;
    period: e.LastEntriesPeriodProperty;
  }>();

  const showNotification = computed(() => {
    if (entriesStore.loading) {
      return false;
    }

    return properties.fallbackUsed && properties.entries.length > 0;
  });
</script>
