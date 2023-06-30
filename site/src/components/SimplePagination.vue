<template>
<hr/>

<button v-if="canShowMore"
        @click.prevent="showMore()">next {{realShowPerPage}}</button>

<span v-if="canShowMore && canHide"> | </span>

<button v-if="canHide"
        @click.prevent="hideAll()">hide all</button>

shown {{showEntries}} / {{total}}

</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import * as t from "@/logic/types";
import { computedAsync } from "@vueuse/core";

const properties = defineProps<{ showFromStart: number,
                                 showPerPage: number,
                                 total: number}>();

const showEntries = ref(properties.showFromStart);

const emit = defineEmits(["update:showEntries"]);


function showMore() {
    showEntries.value += properties.showPerPage;

    if (showEntries.value > properties.total) {
        showEntries.value = properties.total;
    }

    emit('update:showEntries', showEntries.value);
}

function hideAll() {
    showEntries.value = properties.showFromStart;
    emit('update:showEntries', showEntries.value);
}

const realShowPerPage = computed(() => {
    return Math.min(properties.showPerPage, properties.total - showEntries.value);
});

const canHide = computed(() => {
    return showEntries.value > properties.showFromStart;
});

const entriesToShow = computed(() => {
    return properties.entriesIds.slice(0, showEntries.value);
});

const canShowMore = computed(() => {
    return showEntries.value < properties.total;
});


</script>

<style></style>
