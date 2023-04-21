<template>
<div>
  <ul style="list-style: none; padding: 0; margin: 0;">
    <li v-for="tag of displayedTags"
        style="overflow: hidden; text-overflow: ellipsis;"
        :key="tag">
      <value-tag :value="tag"
                 :count="tags[tag]"
                 :selected="!!selectedTags[tag]"
                 @tag:clicked="onTagClicked"/>
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
        delete selectedTags.value[tag];
    }
    else {
        selectedTags.value[tag] = true;
    }
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

<style></style>
