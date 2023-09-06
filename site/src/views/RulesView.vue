<template>
  <side-panel-layout :reload-button="true">
    <template #main-header>
      Rules
      <span v-if="rules">[{{ rules.length }}]</span>
    </template>

    <template #side-menu-item-2>
      Sorted by
      <config-selector
        :values="e.RulesOrderProperties"
        v-model:property="globalSettings.rulesOrder" />
    </template>

    <template #side-footer>
  <tags-filter :tags="tags"
               @tag:stateChanged="onTagStateChanged"/>
    </template>

    <rules-list
      v-if="rules"
      :rules="sortedRules" />
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch} from "vue";
  import {computedAsync} from "@vueuse/core";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import _ from "lodash";
  import * as utils from "@/logic/utils";
  import * as api from "@/logic/api";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
import * as tagsFilterState from "@/logic/tagsFilterState";

const tagsStates = ref<tagsFilterState.TagsFilterState>(new tagsFilterState.TagsFilterState());

  const globalSettings = useGlobalSettingsStore();

globalSettings.mainPanelMode = e.MainPanelMode.Rules;

const requiredTags = ref<{[key: string]: boolean}>({});
const excludedTags = ref<{[key: string]: boolean}>({});
const tagStates = ref<{[key: string]: t.FilterTagState}>({});

  const rules = computedAsync(async () => {
    // force refresh
    globalSettings.dataVersion;
    return await api.getRules();
  }, null);

const tags = computed(() => {
  if (!rules.value) {
    return {};
  }

  const tags: {[key: string]: number} = {};

  for (const rule of rules.value) {
    for (const tag of rule.tags) {
      tags[tag] = (tags[tag] || 0) + 1;
    }
  }

  return tags;
});

  const sortedRules = computed(() => {
    if (!rules.value) {
      return null;
    }

    let sorted = rules.value.slice();

    sorted = tagsStates.value.filterByTags(sorted, (rule) => rule.tags);

    const orderProperties = e.RulesOrderProperties.get(globalSettings.rulesOrder);

    if (!orderProperties) {
      throw new Error(`Invalid order properties: ${globalSettings.rulesOrder}`);
    }

    const orderField = orderProperties.orderField;
    const direction = {asc: -1, desc: 1}[orderProperties.orderDirection];

    if (direction === undefined) {
      throw new Error(`Invalid order direction: ${orderProperties.orderDirection}`);
    }

    sorted = sorted.sort((a: t.Rule, b: t.Rule) => {
      if (globalSettings.rulesOrder === e.RulesOrder.Tags) {
        return utils.compareLexicographically(a.tags, b.tags);
      }

      const valueA = _.get(a, orderField, null);
      const valueB = _.get(b, orderField, null);

      if (valueA === null && valueB === null) {
        return utils.compareLexicographically(a.tags, b.tags);
      }

      if (valueA === null) {
        return 1 * direction;
      }

      if (valueB === null) {
        return -1 * direction;
      }

      if (valueA < valueB) {
        return 1 * direction;
      }

      if (valueA > valueB) {
        return -1 * direction;
      }

      return utils.compareLexicographically(a.tags, b.tags);
    });

    return sorted;
  });

function onTagStateChanged({tag, state}: {tag: string, state: string}) {
    tagsStates.value.onTagStateChanged({tag, state});
}
</script>

<style></style>
