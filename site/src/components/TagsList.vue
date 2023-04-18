<template>
<div>

  <score-rule-constructor v-if="selectedTags.length > 0"
                          :tags="selectedTags"/>

[{{tagsNumber}}]

<template v-for="tag of displayedTags"
          :key="tag">
  <value-tag :value="tag"
             @tag:selected="onTagSelected"
             @tag:deselected="onTagDeselected"/>&nbsp;
</template>

<a href="#" v-if="canShowAll" @click.prevent="showAll=true">more</a>

<a href="#" v-if="canHide" @click.prevent="showAll=false">hide</a>
</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";

const showAll = ref(false);
const showLimit = ref(5);

const selectedTags = ref<string[]>([]);

const properties = defineProps<{ tags: string[]}>();

const tagsNumber = computed(() => {
    return properties.tags.length;
});

const displayedTags = computed(() => {
    if (showAll.value) {
        return preparedTags.value;
    }

    return preparedTags.value.slice(0, showLimit.value);
});

const preparedTags = computed(() => {
    const values = [];

    for (const tag of properties.tags) {
        values.push(tag);
    }

    values.sort();

    return values;
});

const canShowAll = computed(() => {
    return !showAll.value && showLimit.value < preparedTags.value.length;
});

const canHide = computed(() => {
    return showAll.value && showLimit.value < preparedTags.value.length;
});

function onTagSelected(tag: string) {
    selectedTags.value.push(tag);
    showAll.value = true;
}

function onTagDeselected(tag: string) {
    selectedTags.value = selectedTags.value.filter(x => x !== tag);
}


</script>

<style></style>
