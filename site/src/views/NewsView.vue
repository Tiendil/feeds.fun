<template>
  <side-panel-layout>
    <template #side-menu-item-1>
      For the last
      <config-selector
        :values="e.LastEntriesPeriodProperties"
        v-model:property="globalSettings.lastEntriesPeriod" />
    </template>

    <template #side-menu-item-2>
      Sorted by
      <config-selector
        :values="e.EntriesOrderProperties"
        v-model:property="globalSettings.entriesOrder" />
    </template>

    <template #side-menu-item-3>
      Show tags:
      <config-flag
        v-model:flag="globalSettings.showEntriesTags"
        on-text="yes"
        off-text="no" />
    </template>

    <template #side-menu-item-4>
      Show already read:
      <config-flag
        v-model:flag="globalSettings.showRead"
        on-text="yes"
        off-text="no" />
    </template>

    <template #side-footer>
      <tags-filter :tags="entriesStore.reportTagsCount"
                   @tag:stateChanged="onTagStateChanged"/>
    </template>

    <template #main-header>
      News
      <span v-if="entriesNumber > 0">[{{ entriesNumber }}]</span>
    </template>

    <template #main-footer> </template>

    <template v-if="!hasEntries && !entriesStore.firstTimeEntriesLoading">
      <p>It looks like you have no news to read.</p>
      <p> Try to subscribe for the feeds collections that we are preparing for you! </p>
      <feeds-collections />
    </template>

    <entries-list
      :entriesIds="entriesStore.entriesReport"
      :time-field="timeField"
      :show-tags="globalSettings.showEntriesTags"
      :showFromStart="25"
      :showPerPage="25" />
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch} from "vue";
  import {computedAsync} from "@vueuse/core";
  import * as api from "@/logic/api";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useEntriesStore} from "@/stores/entries";

  const globalSettings = useGlobalSettingsStore();
  const entriesStore = useEntriesStore();

  globalSettings.mainPanelMode = e.MainPanelMode.Entries;

  globalSettings.updateDataVersion();

  const entriesNumber = computed(() => {
    return entriesStore.entriesReport.length;
  });

  const hasEntries = computed(() => {
    return entriesNumber.value > 0;
  });

  const timeField = computed(() => {
    const orderProperties = e.EntriesOrderProperties.get(globalSettings.entriesOrder);

    if (orderProperties === undefined) {
      throw new Error(`Unknown entries order: ${globalSettings.entriesOrder}`);
    }

    return orderProperties.timeField;
  });

function onTagStateChanged({tag, state}: {tag: string, state: string}) {
  if (state === "required") {
    entriesStore.requireTag({tag: tag});
  } else if (state === "excluded") {
    entriesStore.excludeTag({tag: tag});
  } else if (state === "none") {
    entriesStore.resetTag({tag: tag});
  } else {
    throw new Error(`Unknown tag state: ${state}`);
  }
}
</script>

<style></style>
