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
      <tags-filter :tags="tagsCount" />
    </template>

    <div class="ffun-info-good">
      <p
        >You can create new rules on the
        <a
          href="#"
          @click.prevent="goToNews()"
          >news</a
        >
        tab.</p
      >
    </div>

    <rules-list
      v-if="rules"
      :rules="sortedRules" />
  </side-panel-layout>
</template>

<script lang="ts" setup>
  // TODO: update rules visualization with excluded tags
  // TODO: update rules filtering?
  import {computed, ref, onUnmounted, watch, provide} from "vue";
  import {useRouter} from "vue-router";
  import {computedAsync} from "@vueuse/core";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import _ from "lodash";
  import * as utils from "@/logic/utils";
  import * as api from "@/logic/api";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as tagsFilterState from "@/logic/tagsFilterState";

  const router = useRouter();

  const tagsStates = ref<tagsFilterState.Storage>(new tagsFilterState.Storage());

  provide("tagsStates", tagsStates);

  const globalSettings = useGlobalSettingsStore();

  globalSettings.mainPanelMode = e.MainPanelMode.Rules;

  function goToNews() {
    router.push({name: e.MainPanelMode.Entries, params: {}});
  }

  const rules = computedAsync(async () => {
    // force refresh
    globalSettings.dataVersion;
    return await api.getRules();
  }, null);

  const tagsCount = computed(() => {
    if (!rules.value) {
      return {};
    }

    const tags: {[key: string]: number} = {};

    for (const rule of rules.value) {
      for (const tag of rule.requiredTags) {
        tags[tag] = (tags[tag] || 0) + 1;
      }

      for (const tag of rule.excludedTags) {
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

    sorted = tagsStates.value.filterByTags(sorted, (rule) => rule.requiredTags.concat(rule.excludedTags));

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
        // TODO: move requiredTags.concat(a.excludedTags) to a class method
        return utils.compareLexicographically(
          a.requiredTags.concat(a.excludedTags),
          b.requiredTags.concat(a.excludedTags)
        );
      }

      const valueA = _.get(a, orderField, null);
      const valueB = _.get(b, orderField, null);

      if (valueA === null && valueB === null) {
        return utils.compareLexicographically(a.requiredTags.concat(a.excludedTags), b.requiredTags.concat(b.excludedTags));
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

      return utils.compareLexicographically(a.requiredTags.concat(a.excludedTags), b.requiredTags.concat(b.excludedTags));
    });

    return sorted;
  });
</script>
