<template>
  <div>
    <ul
      v-if="displayedSelectedTags.length > 0"
      class="pl-0 mb-0">
      <li
        v-for="tag of displayedSelectedTags"
        :key="tag"
        class="whitespace-nowrap line-clamp-1">
        <ffun-tag
          class="ml-1"
          :uid="tag"
          :count="tags[tag] ?? 0"
          :show-switch="true"
          cssModifier="ffun-tags-filter"
          count-mode="no"
          change-source="tag_filter" />
      </li>
    </ul>

    <rule-constructor v-if="showCreateRule" />

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
          cssModifier="ffun-tags-filter"
          count-mode="prefix"
          changeSource="tag_filter" />
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

  const properties = defineProps<{tags: {[key: string]: number}; showCreateRule?: boolean}>();

  const showFromStart = ref(25);

  const showEntries = ref(showFromStart.value);

  const tagNameFilter = ref("");

  function createTagComparator() {
    const counts = properties.tags;

    function tagComparator(a: string, b: string) {
      const aCount = counts[a];
      const bCount = counts[b];

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

    return tagComparator;
  }

  const displayedSelectedTags = computed(() => {
    let values = Object.keys(tagsStates.value.selectedTags);

    const comparator = createTagComparator();
    values.sort(comparator);

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

  const _sortedTags = computed(() => {
    let values = Object.keys(properties.tags);

    const comparator = createTagComparator();

    values.sort(comparator);

    return values;
  });

  const _visibleTags = computed(() => {
    let values = _sortedTags.value.slice();

    const textFilter = tagNameFilter.value.trim().toLowerCase();

    const selectedTags = Object.keys(tagsStates.value.selectedTags);

    values = values.filter((tag) => {
      if (selectedTags.includes(tag)) {
        return false;
      }

      if (!textFilter) {
        return true;
      }

      const tagInfo = tagsStore.tags[tag];

      if (tagInfo === undefined || tagInfo.name === null) {
        return tag.includes(tagNameFilter.value);
      }

      return tagInfo.name.includes(tagNameFilter.value);
    });

    return values;
  });

  const displayedTags = computed(() => {
    return _visibleTags.value.slice(0, showEntries.value);
  });
</script>
