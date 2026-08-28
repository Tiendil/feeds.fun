<template>
  <div>
    <div
      v-if="tagsStates.hasSelectedTags"
      class="flex items-center">
      <div class="flex-none">
        <score-selector
          class="inline-block mr-2 my-auto"
          v-model="currentScore" />
      </div>

      <ui-button
        variant="primary"
        size="compact"
        class="my-1 flex-grow"
        @click.prevent="createOrUpdateRule()"
        >Create Rule</ui-button
      >
    </div>

    <template v-else>
      <ui-notice
        v-if="showSuccess"
        tone="success"
        >Rule created.</ui-notice
      >
      <ui-empty-state v-else> Select tags to create a rule. </ui-empty-state>
    </template>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref, inject, watch} from "vue";
  import type {Ref} from "vue";
  import {useTagsStore} from "@/stores/tags";
  import type * as tagsFilterState from "@/logic/tagsFilterState";
  import * as asserts from "@/logic/asserts";
  import * as api from "@/logic/api";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

  const tagsStore = useTagsStore();

  const globalSettings = useGlobalSettingsStore();

  const currentScore = ref(1);

  const showSuccess = ref(false);

  const tagsStates = inject<Ref<tagsFilterState.Storage>>("tagsStates");
  asserts.defined(tagsStates);

  watch(
    () => tagsStates.value.hasSelectedTags,
    () => {
      // This condition is needed to prevent immediate reset of the success message
      // right after the rule is created in createOrUpdateRule
      if (tagsStates.value.hasSelectedTags) {
        showSuccess.value = false;
      }
    }
  );

  async function createOrUpdateRule() {
    asserts.defined(tagsStates);
    await api.createOrUpdateRule({
      requiredTags: Object.keys(tagsStates.value.requiredTags),
      excludedTags: Object.keys(tagsStates.value.excludedTags),
      score: currentScore.value
    });

    tagsStates.value.clear();

    showSuccess.value = true;

    // this line leads to the reloading of news and any other data
    // not an elegant solution, but it works with the current API implementation
    // TODO: try to refactor to only update scores of news:
    //       - without reloading
    //       - maybe, without reordering too
    globalSettings.updateDataVersion();
  }
</script>
