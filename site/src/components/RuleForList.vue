<template>
<div>
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

    <score-selector
      class="flex-shrink-0 mr-2"
      :modelValue="rule.score"
      @input="updateSelected" />

    <div class="flex-grow">
      <template
        v-for="tag of rule.tags"
        :key="tag">
        <ffun-tag :uid="tag" />&nbsp;
      </template>
  </div>

  </div>

<p v-if="scoreChanged" class="ffun-info-good">
  Score updated <a href="#" class="ffun-form-button" @click.prevent="scoreChanged = false">close</a>
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
      tags: properties.rule.tags
    });

    scoreChanged.value = true;

    globalSettings.updateDataVersion();
  }

</script>
