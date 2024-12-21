<template>
<div>

  <div v-if="displayedSelectedTags.length > 0">
    <ul
      class="pl-0 mb-0">
      <li
        v-for="tag of displayedSelectedTags"
        :key="tag"
        class="whitespace-nowrap line-clamp-1">
        <ffun-tag
          class="ml-1"
          :uid="tag"
          :count="tags[tag] ?? 0"
          :showSwitch="true"
          count-mode="no" />
      </li>
    </ul>

    <div class="flex items-center">

      <div class="flex-none">
        <score-selector
          v-if="displayedSelectedTags.length > 0"
          class="inline-block mr-2 my-auto"
          v-model="currentScore" />
      </div>

      <a
        class="ffun-form-button p-1 my-1 block text-center inline-block flex-grow"
        v-if="displayedSelectedTags.length > 0"
        href="#"
        @click.prevent="createOrUpdateRule()"
        >Create Rule</a
                      >
    </div>
  </div>

    <p
      class="ffun-info-good"
      v-else>
      Select tags to create a rule.
    </p>

    <input
      class="ffun-input w-full"
      type="text"
      placeholder="Input part of a tag…"
      v-model="tagNameFilter" />

    <ul
      v-if="displayedTags.length > 0"
      class="pl-0 mb-0">
      <li
        v-for="tag of displayedTags"
        :key="tag"
        class="truncate">
        <ffun-tag
          :uid="tag"
          :count="tags[tag]"
          count-mode="prefix" />
      </li>
    </ul>

    <hr />

    <simple-pagination
      :showFromStart="showFromStart"
      :showPerPage="10"
      :total="totalTags"
      :counterOnNewLine="true"
      v-model:showEntries="showEntries" />
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

  const properties = defineProps<{tags: {[key: string]: number}}>();

  const showFromStart = ref(25);

  const showEntries = ref(showFromStart.value);

  const tagNameFilter = ref("");

  function tagComparator(a: string, b: string) {
    const aCount = properties.tags[a];
    const bCount = properties.tags[b];

    if (aCount > bCount) {
      return -1;
    }

    if (aCount < bCount) {
      return 1;
    }

    if (a > b) {
      return 1;
    }

    if (a < b) {
      return -1;
    }

    return 0;
  }

  const displayedSelectedTags = computed(() => {
    let values = Object.keys(tagsStates.value.selectedTags);

    values = values.filter((tag) => {
      return tagsStates.value.selectedTags[tag] === true;
    });

    values.sort(tagComparator);

    return values;
  });

  const totalTags = computed(() => {
    // TODO: this is not correct, because selected tags are treated differently
    //       depending on their status: required or excluded.
    //       I.e. by excluding tag `x` you exclude concreate entries => you can exclude more tags,
    //       if they only belong to the excluded entries)
    //       => value is not accurate, but it is ok for now
    return Object.keys(properties.tags).length + Object.keys(tagsStates.value.selectedTags).length;
  });

  const displayedTags = computed(() => {
    let values = Object.keys(properties.tags);

    if (values.length === 0) {
      return [];
    }

    values = values.filter((tag) => {
      return tagsStates.value.selectedTags[tag] !== true;
    });

    values = values.filter((tag) => {
      const tagInfo = tagsStore.tags[tag];

      if (tagInfo === undefined || tagInfo.name === null) {
        return tag.includes(tagNameFilter.value);
      }

      return tagInfo.name.includes(tagNameFilter.value);
    });

    values.sort(tagComparator);

    values = values.slice(0, showEntries.value);

    return values;
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
