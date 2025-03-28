<template>

  <!-- TODO: Hide when loading new news from the server -->
  <!-- Currently, after changing the period, this message does not disappear -->
  <!-- until the backend returns a new response -->
  <!-- It confuses users because the period size is changing in the text at the beginning of the request. -->
  <div v-if="allEntriesAreOlderThanPeriod" class="ffun-info-common">
    <p>
      We have not found any news that is newer than {{ period.text }}, so we loaded some older ones.
    </p>
  </div>

</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch, provide} from "vue";
  import {useRoute, useRouter} from "vue-router";
  import {computedAsync} from "@vueuse/core";
  import * as api from "@/logic/api";
  import * as tagsFilterState from "@/logic/tagsFilterState";
  import * as e from "@/logic/enums";
  import * as utils from "@/logic/utils";
  import type * as t from "@/logic/types";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useEntriesStore} from "@/stores/entries";
import _ from "lodash";

const entriesStore = useEntriesStore();

  const properties = defineProps<{
    entries: t.EntryId[];
    period: t.LastEntriesPeriodProperty
  }>();

const allEntriesAreOlderThanPeriod = computed(() => {
  console.log("loading", entriesStore.loading);
  if (entriesStore.loading) {
    return false;
  }

  if (properties.entries.length == 0) {
    return false;
  }

  return properties.entries.every((entryId) => {
    const entry = entriesStore.entries[entryId];
    return entry.publishedAt < Date.now() - properties.period.seconds * 1000;
  });
});

</script>
