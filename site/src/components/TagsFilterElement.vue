<template>
  <li class="filter-element">
    <ffun-tag
      :uid="tag"
      :count="count"
      :count-mode="countMode"
      :mode="mode"
      @tag:clicked="onTagClicked">
      <template #start>
        <a
          v-if="selected"
          href="#"
          @click.prevent="deselect(tag)"
          >[X]</a
        >
      </template>
    </ffun-tag>
  </li>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import {useEntriesStore} from "@/stores/entries";

  const entriesStore = useEntriesStore();

  const properties = defineProps<{
    tag: string;
    count: number;
    selected: boolean;
  }>();

  const emit = defineEmits(["tag:selected", "tag:deselected"]);

  const countMode = computed(() => {
    if (properties.selected) {
      return "no";
    }

    return "prefix";
  });

  const mode = computed(() => {
    if (entriesStore.requiredTags[properties.tag]) {
      return "required";
    } else if (entriesStore.excludedTags[properties.tag]) {
      return "excluded";
    } else if (properties.selected) {
      return "selected";
    }

    return null;
  });

  function onTagClicked(tag: string) {
    if (entriesStore.requiredTags[properties.tag]) {
      switchToExcluded(tag);
    } else {
      switchToRequired(tag);
    }
  }

  function switchToExcluded(tag: string) {
    entriesStore.excludeTag({tag: tag});
    emit("tag:selected", properties.tag);
  }

  function switchToRequired(tag: stirng) {
    entriesStore.requireTag({tag: tag});
    emit("tag:selected", properties.tag);
  }

  function deselect(tag: stirng) {
    entriesStore.resetTag({tag: tag});
    emit("tag:deselected", properties.tag);
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
