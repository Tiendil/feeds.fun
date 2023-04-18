<template>
<div>

  <rule-constructor v-if="selectedTagsList.length > 0"
                    :tags="selectedTagsList"
                    @rule-constructor:created="onRuleCreated"/>

[{{tagsNumber}}]

<template v-for="tag of displayedTags"
          :key="tag">
  <value-tag :value="tag"
             :selected="!!selectedTags[tag]"
             @tag:clicked="onTagClicked"/>&nbsp;
</template>

<a href="#" v-if="canShowAll" @click.prevent="showAll=true">more</a>

<a href="#" v-if="canHide" @click.prevent="showAll=false">hide</a>
</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";

const showAll = ref(false);
const showLimit = ref(5);

const selectedTags = ref<{ [key: string]: boolean }>({});

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

function onTagClicked(tag: string) {
    if (!!selectedTags.value[tag]) {
        delete selectedTags.value[tag];
    }
    else {
        selectedTags.value[tag] = true;
        showAll.value = true;
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


function onRuleCreated() {
    selectedTags.value = {};
}


</script>

<style></style>
