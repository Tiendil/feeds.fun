<template>
  <div>
    <ul
      v-if="displayedSelectedTags.length > 0"
      style="list-style: none; padding: 0; margin: 0">
      <tags-filter-element
        v-for="tag of displayedSelectedTags"
        :key="tag"
        :tag="tag"
        :count="tags[tag] ?? 0"
        :selected="true"
        @tag:selected="onTagSelected"
        @tag:deselected="onTagDeselected" />
    </ul>

    <input
      type="text"
      placeholder="Input part of tag..."
      v-model="tagNameFilter" />

    <ul
      v-if="displayedTags.length > 0"
      style="list-style: none; padding: 0; margin: 0">
      <tags-filter-element
        v-for="tag of displayedTags"
        :key="tag"
        :tag="tag"
        :count="tags[tag]"
        :selected="false"
        @tag:selected="onTagSelected"
        @tag:deselected="onTagDeselected" />
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
  import {computed, ref} from "vue";
  import {useTagsStore} from "@/stores/tags";

  const tagsStore = useTagsStore();

  const selectedTags = ref<{[key: string]: boolean}>({});

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
    let values = Object.keys(selectedTags.value);

    values = values.filter((tag) => {
      return selectedTags.value[tag] === true;
    });

    values.sort(tagComparator);

    return values;
  });

  const totalTags = computed(() => {
    // TODO: this is not correct, because selected tags are treated differently
    //       depending on their status: required or excluded.
    //       => value is not accurate, but it is ok for now
    return Object.keys(properties.tags).length + Object.keys(selectedTags.value).length;
  });

  const displayedTags = computed(() => {
    let values = Object.keys(properties.tags);

    if (values.length === 0) {
      return [];
    }

    values = values.filter((tag) => {
      return selectedTags.value[tag] !== true;
    });

    values = values.filter((tag) => {
      const tagInfo = tagsStore.tags[tag];

      if (tagInfo === undefined) {
        return tag.includes(tagNameFilter.value);
      }

      return tagInfo.name.includes(tagNameFilter.value);
    });

    values.sort(tagComparator);

    values = values.slice(0, showEntries.value);

    return values;
  });

  function onTagSelected(tag: string) {
    selectedTags.value[tag] = true;
  }

  function onTagDeselected(tag: string) {
    selectedTags.value[tag] = false;
  }
</script>

<style scoped>
  .filter-element {
    overflow: hidden;
    white-space: nowrap;
  }

  .filter-element value-tag {
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
