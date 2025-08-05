<template>
  <side-panel-layout :reload-button="true">
    <template #main-header>
      Rules
      <span v-if="rules">[{{ rulesNumber }}]</span>
    </template>

    <template #side-menu-item-2>
      Sorted by
      <config-selector
        :values="e.RulesOrderProperties"
        v-model:property="globalSettings.rulesOrder" />
    </template>

    <template #side-footer>
      <tags-filter
        :tags="tagsCount"
        :show-create-rule="false" />
    </template>

    <div class="ffun-info-common mb-2">
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
      :loading="loading"
      :rules="sortedRules" />
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch, provide} from "vue";
  import {useRoute, useRouter} from "vue-router";
  import {computedAsync} from "@vueuse/core";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import _ from "lodash";
  import * as utils from "@/logic/utils";
  import * as api from "@/logic/api";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as tagsFilterState from "@/logic/tagsFilterState";

  const route = useRoute();
  const router = useRouter();

  const tagsStates = ref<tagsFilterState.Storage>(new tagsFilterState.Storage());

  provide("tagsStates", tagsStates);
  provide("eventsViewName", "rules");

  const globalSettings = useGlobalSettingsStore();

  tagsFilterState.setSyncingTagsWithRoute({
    tagsStates: tagsStates.value as unknown as tagsFilterState.Storage,
    route,
    router
  });

  tagsFilterState.setSyncingTagsSidebarPoint({
    tagsStates: tagsStates.value as unknown as tagsFilterState.Storage,
    globalSettings
  });

  globalSettings.mainPanelMode = e.MainPanelMode.Rules;

  function goToNews() {
    router.push({name: e.MainPanelMode.Entries, params: {}});
  }

  const loading = computed(() => rules.value === null);

  const rules = computedAsync(async () => {
    // force refresh
    globalSettings.dataVersion;
    return await api.getRules();
  }, null);

  const sortedRules = computed(() => {
    if (!rules.value) {
      return null;
    }

    let sorted = rules.value.slice();

    sorted = tagsStates.value.filterByTags(sorted, (rule) => rule.tags);

    const orderProperties = e.RulesOrderProperties.get(globalSettings.rulesOrder as any);

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

  const rulesNumber = computed(() => {
    return sortedRules.value ? sortedRules.value.length : 0;
  });

  const tagsCount = computed(() => {
    return utils.countTags(sortedRules.value);
  });
</script>
