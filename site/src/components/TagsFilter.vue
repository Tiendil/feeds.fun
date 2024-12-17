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
          :showSwitch="true"
          count-mode="no"/>
      </li>
    </ul>

    <input
      class="ffun-input w-full"
      type="text"
      placeholder="Input part of tag..."
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
          count-mode="prefix"/>
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
  import {useTagsStore} from "@/stores/tags";
  import type * as tagsFilterState from "@/logic/tagsFilterState";
  const tagsStore = useTagsStore();

const tagsStates = inject<tagsFilterState.Storage>('tagsStates');

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

</script>
