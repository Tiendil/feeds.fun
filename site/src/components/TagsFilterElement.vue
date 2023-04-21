<template>
<li class="filter-element">

  <div v-if="selected" style="display: inline-block; margin-right: 0.25rem;">
    <a v-if="entriesStore.requiredTags[tag]" href="#" @click.prevent="switchToExcluded(tag)">[X]</a>
    <a v-if="entriesStore.excludedTags[tag]" href="#" @click.prevent="switchToRequired(tag)">[V]</a>
  </div>

  <value-tag :value="tag"
             :count="count"
             :selected="selected"
             @tag:clicked="onTagClicked">
  </value-tag>
</li>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import { useEntriesStore } from "@/stores/entries";

const entriesStore = useEntriesStore();

const properties = defineProps<{ tag: string,
                                 count: number,
                                 selected: boolean }>();

const emit = defineEmits(["tag:clicked"]);

function onTagClicked(tag: string) {
    if (properties.selected) {
        entriesStore.resetTag({tag: tag});
    }
    else {
        entriesStore.requireTag({tag: tag});
    }

    emit('tag:clicked', properties.tag);
}

function switchToExcluded(tag: string) {
    entriesStore.excludeTag({tag: tag});
}

function switchToRequired(tag: stirng) {
    entriesStore.requireTag({tag: tag});
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
