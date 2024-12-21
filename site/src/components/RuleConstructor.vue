<template>
<div>

  <div v-if="hasSelectedTags"
       class="flex items-center">

    <div class="flex-none">
      <score-selector
        class="inline-block mr-2 my-auto"
        v-model="currentScore" />
    </div>

    <a
      class="ffun-form-button p-1 my-1 block text-center inline-block flex-grow"
      href="#"
      @click.prevent="createOrUpdateRule()"
      >Create Rule</a
                    >
  </div>

  <p
    class="ffun-info-good"
    v-else>
    Select tags to create a rule.
  </p>

</div>
</template>

<script lang="ts" setup>
  // TODO: do not reset scores on tag selection change
  import {computed, ref, inject} from "vue";
  import type {Ref} from "vue";
  import {useTagsStore} from "@/stores/tags";
  import type * as tagsFilterState from "@/logic/tagsFilterState";
import * as asserts from "@/logic/asserts";
import * as api from "@/logic/api";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

const tagsStore = useTagsStore();

  const globalSettings = useGlobalSettingsStore();

  const currentScore = ref(1);

  const tagsStates = inject<Ref<tagsFilterState.Storage>>("tagsStates");
  asserts.defined(tagsStates);

  const hasSelectedTags = computed(() => {
    let values = Object.keys(tagsStates.value.selectedTags);

    values = values.filter((tag) => {
      return tagsStates.value.selectedTags[tag] === true;
    });

    return values.length > 0;
  });

  async function createOrUpdateRule() {
    await api.createOrUpdateRule({requiredTags: tagsStates.value.requiredTagsList(),
                                  excludedTags: tagsStates.value.excludedTagsList(),
                                  score: currentScore.value});

    // this line leads to the reloading of news and any other data
    // not an elegant solution, but it works with the current API implementation
    // TODO: try to refactor to only update scores of news:
    //       - without reloading
    //       - maybe, without reordering too
    globalSettings.updateDataVersion();
  }

</script>
