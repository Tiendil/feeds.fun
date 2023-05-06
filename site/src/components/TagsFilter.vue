<template>
<div>

  <ul v-if="displayedTags.length > 0" style="list-style: none; padding: 0; margin: 0;">
    <tags-filter-element v-for="tag of displayedSelectedTags"
                         :key="tag"
                         :tag="tag"
                         :count="tags[tag] ?? 0"
                         :selected="true"
                         @tag:clicked="onTagClicked"/>
  </ul>

  <ul v-if="displayedTags.length > 0" style="list-style: none; padding: 0; margin: 0;">
    <tags-filter-element v-for="tag of displayedTags"
                         :key="tag"
                         :tag="tag"
                         :count="tags[tag]"
                         :selected="false"
                         @tag:clicked="onTagClicked"/>
  </ul>
</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";

const selectedTags = ref<{ [key: string]: boolean }>({});

const properties = defineProps<{ tags: {[key: string]: number} }>();


function tagComparator(a, b) {
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

const displayedTags = computed(() => {

    let values = Object.keys(properties.tags);

    if (values.length === 0) {
        return [];
    }

    values = values.filter((tag) => {
        return selectedTags.value[tag] !== true;
    });

    values.sort(tagComparator);

    // TODO: move to configs or even to the side panel
    values = values.slice(0, 100);

    return values;
});

function onTagClicked(tag: string) {
    if (!!selectedTags.value[tag]) {
        selectedTags.value[tag] = false;
    }
    else {
        selectedTags.value[tag] = true;
    }
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
