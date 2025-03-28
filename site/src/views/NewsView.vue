<template>
  <side-panel-layout>
    <template #side-menu-item-1>
      For
      <config-selector
        :values="e.LastEntriesPeriodProperties"
        v-model:property="globalSettings.lastEntriesPeriod" />
    </template>

    <template #side-menu-item-2>
      Sort by
      <!-- Remember that we should use entriesStore.activeOrderProperties everywhere in the News view-->
      <!-- Here, It should be in sync with this selector (and globalSettings.entriesOrder) on the NewsView, -->
      <!-- so, it should work fine -->
      <config-selector
        :values="e.EntriesOrderProperties"
        v-model:property="globalSettings.entriesOrder" />
    </template>

    <template #side-menu-item-3>
      Show read

      <config-flag
        style="min-width: 2.5rem"
        v-model:flag="globalSettings.showRead"
        on-text="no"
        off-text="yes" />

      <button
        class="ffun-form-button py-0 ml-1"
        title='Undo last "mark read" operation'
        :disabled="!entriesStore.canUndoMarkRead"
        @click="entriesStore.undoMarkRead()">
        ↶
      </button>
    </template>

    <template #side-footer>
      <tags-filter
        :tags="tagsCount"
        :show-create-rule="true" />
    </template>

    <template #main-header>
      News
      <span v-if="entriesNumber > 0">[{{ entriesNumber }}]</span>
    </template>

    <template #main-footer> </template>

    <notifications
      v-if="entriesStore.loadedEntriesReport !== null"
      :create-rule-help="hasEntries && !hasRules"
      :api-key="true"
      :collections-notification_="!hasEntries"
      :collections-warning_="false" />

    <entries-list
      :loading="entriesStore.loading"
      :entriesIds="entriesReport"
      :time-field="entriesStore.activeOrderProperties.timeField"
      :tags-count="tagsCount"
      :show-score="true"
      :showFromStart="25"
      :showPerPage="25" />
  </side-panel-layout>
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

  const globalSettings = useGlobalSettingsStore();
  const entriesStore = useEntriesStore();

  const route = useRoute();
  const router = useRouter();

  entriesStore.setNewsMode();

  const tagsStates = ref<tagsFilterState.Storage>(new tagsFilterState.Storage());

  provide("tagsStates", tagsStates);
  provide("eventsViewName", "news");

  tagsFilterState.setSyncingTagsWithRoute({
    tagsStates: tagsStates.value as unknown as tagsFilterState.Storage,
    route,
    router
  });

  globalSettings.mainPanelMode = e.MainPanelMode.Entries;

  globalSettings.updateDataVersion();

  const entriesReport = computed(() => {
    let report = entriesStore.visibleEntries.slice();

    report = tagsStates.value.filterByTags(report, (entryId) => entriesStore.entries[entryId].tags);
    return report;
  });

  const tagsCount = computed(() => {
    const entriesToProcess = entriesReport.value.map((entryId) => entriesStore.entries[entryId]);

    return utils.countTags(entriesToProcess);
  });

  const entriesNumber = computed(() => {
    return entriesReport.value.length;
  });

  const hasEntries = computed(() => {
    return entriesNumber.value > 0;
  });

  const hasRules = computed(() => {
    if (entriesStore.loading) {
      return false;
    }

    if (entriesStore.loadedEntriesReport === null) {
      return false;
    }

    // TODO: it is a heuristic (score could be 0 even with rules)
    //       must be refactored to something more stable
    for (const entryId of entriesStore.loadedEntriesReport) {
      if (entriesStore.entries[entryId].score != 0) {
        return true;
      }
    }
    return false;
  });
</script>

<style></style>
