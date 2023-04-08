<template>

<template v-for="tag of displayedTags">
    <value-tag :value="tag"/>&nbsp;
</template>

<a href="#" v-if="canShowAll" @click="showAll=true">more</a>

<a href="#" v-if="canHide" @click="showAll=false">hide</a>

</template>

<script lang="ts" setup>
import { computed, ref } from "vue";

const showAll = ref(false);
const showLimit = ref(5);

const properties = defineProps<{ tags: string[]}>();

const displayedTags = computed(() => {
    if (showAll.value) {
        return preparedTags.value;
    }

    return preparedTags.value.slice(0, showLimit.value);
});

const preparedTags = computed(() => {
    const values = [];

    for (const tag of properties.tags) {
        const [type_, value] = tag.split(":");
        values.push(value);
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


</script>

<style></style>
