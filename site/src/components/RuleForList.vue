<template>
  <div>
    <div
      v-if="rule !== null"
      class="flex mb-1">
      <div class="ffun-body-list-icon-column">
        <a
          href="#"
          class="ti ti-x text-red-500 hover:text-red-600"
          title="Remove this rule"
          @click.prevent="deleteRule()">
        </a>
      </div>

      <div class="flex-shrink-0 min-w-fit mr-2">
        <score-selector
          :modelValue="rule.score"
          @input="updateSelected" />
      </div>

      <div class="flex-grow">
        <rule-tag
          v-for="tag of rule.allTags"
          :key="tag"
          :uid="tag"
          :css-modifier="cssModifiers[tag]" />
      </div>
    </div>

    <p
      v-if="scoreChanged"
      class="ffun-info-good">
      Score updated
      <a
        href="#"
        class=""
        @click.prevent="scoreChanged = false"
        >[close]</a
      >
    </p>
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

  const scoreChanged = ref(false);

  async function deleteRule() {
    await api.deleteRule({id: properties.rule.id});
    globalSettings.updateDataVersion();
  }

  async function updateSelected(event: Event) {
    const target = event.target as HTMLInputElement;
    const newScore = Number(target.value);

    await api.updateRule({
      id: properties.rule.id,
      score: newScore,
      requiredTags: properties.rule.requiredTags,
      excludedTags: properties.rule.excludedTags
    });

    scoreChanged.value = true;

    globalSettings.updateDataVersion();
  }

  const cssModifiers: {[key: string]: string} = {};

  for (const tag of properties.rule.allTags) {
    if (properties.rule.excludedTags.includes(tag)) {
      cssModifiers[tag] = "negative";
      continue;
    }
    cssModifiers[tag] = "positive";
  }
</script>
