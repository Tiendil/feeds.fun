<template>

  <div
    v-if="rule !== null"
    class="flex mb-1">
    <div class="flex-shrink-0 min-w-fit mr-2">
      <a
        href="#"
        class="ffun-normal-link"
        @click.prevent="deleteRule()">
        remove
      </a>
    </div>

    <rule-score-updater
      class="flex-shrink-0 mr-2"
      :score="rule.score"
      :rule-id="rule.id"
      :tags="rule.tags" />

    <div class="flex-grow">
      <template
        v-for="tag of rule.tags"
        :key="tag">
        <ffun-tag :uid="tag" />&nbsp;
      </template>
    </div>

  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

  const globalSettings = useGlobalSettingsStore();

  const properties = defineProps<{rule: t.Rule}>();

  async function deleteRule() {
    await api.deleteRule({id: properties.rule.id});
    globalSettings.updateDataVersion();
  }
</script>
