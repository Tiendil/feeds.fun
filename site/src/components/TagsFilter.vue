<template>
<div>
  <ul style="list-style: none; padding: 0; margin: 0;">
    <li v-for="tag of displayedTags"
        class="filter-element"
        :key="tag">
       <value-tag :value="tag"
                 :count="tags[tag]"
                 :selected="!!selectedTags[tag]"
                  @tag:clicked="onTagClicked">
         <template #start>
           <div v-if="!!selectedTags[tag]" style="display: inline-block; margin-right: 0.25rem;">
             <a v-if="entriesStore.requiredTags[tag]" href="#" @click.prevent="switchToExcluded(tag)">[X]</a>
             <a v-if="entriesStore.excludedTags[tag]" href="#" @click.prevent="switchToRequired(tag)">[V]</a>
           </div>
         </template>
       </value-tag>
    </li>
  </ul>
</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import { useEntriesStore } from "@/stores/entries";

const entriesStore = useEntriesStore();

const selectedTags = ref<{ [key: string]: boolean }>({});

const properties = defineProps<{ tags: {[key: string]: number} }>();

const displayedTags = computed(() => {

    let values = Object.keys(properties.tags);

    // TODO: move to configs or even to the side panel
    values = values.slice(0, 100);

    if (values.length === 0) {
        return [];
    }

    values.sort((a, b) => {
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
    });

    return values;
});

function onTagClicked(tag: string) {
    if (!!selectedTags.value[tag]) {
        entriesStore.resetTag({tag: tag});
        selectedTags.value[tag] = false;
    }
    else {
        entriesStore.requireTag({tag: tag});
        selectedTags.value[tag] = true;
    }
}

function switchToExcluded(tag: string) {
    entriesStore.excludeTag({tag: tag});
}

function switchToRequired(tag: stirng) {
    entriesStore.requireTag({tag: tag});
}

const selectedTagsList = computed(() => {
    const values = [];

    for (const tag in selectedTags.value) {
        values.push(tag);
    }

    values.sort();

    return values;
});


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
