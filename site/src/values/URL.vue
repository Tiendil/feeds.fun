<template>
  <a :href="value" target="_blank" rel="noopener noreferrer">{{renderedText}}</a>
</template>

<script lang="ts" setup>
import { computed } from "vue";
import * as t from "@/logic/types";

const properties = defineProps<{ value: t.URL,
                                 text?: string|null}>();

const renderedText = computed(() => {
    if (properties.text) {
        return properties.text;
    }

    return properties.value;
});

</script>

<style></style>
