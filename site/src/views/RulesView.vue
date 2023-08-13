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
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";

  const globalSettings = useGlobalSettingsStore();

  globalSettings.mainPanelMode = e.MainPanelMode.Rules;

  const rules = computedAsync(async () => {
    // force refresh
    globalSettings.dataVersion;
    return await api.getRules();
  }, null);

  const sortedRules = computed(() => {
    if (!rules.value) {
      return null;
    }

    const orderProperties = e.RulesOrderProperties.get(globalSettings.rulesOrder);
    const orderField = orderProperties.orderField;
    const direction = {asc: -1, desc: 1}[orderProperties.orderDirection];

    let sorted = rules.value.slice();

    sorted = sorted.sort((a: t.Rule, b: t.Rule) => {
      if (globalSettings.rulesOrder === e.RulesOrder.Tags) {
        return utils.compareLexicographically(a.tags, b.tags);
      }

      const valueA = _.get(a, orderField, null);
      const valueB = _.get(b, orderField, null);

      if (valueA === null && valueB === null) {
        return 0;
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

      return 0;

    });

    return sorted;

  }, null);
</script>

<style></style>
