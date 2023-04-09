<template>
<div>
{{renderedText}}
</div>
</template>

<script lang="ts" setup>
import { computed } from "vue";

const properties = defineProps<{ value: number}>();

const renderedText = computed(() => {
    return properties.value;
});

</script>

<style></style>
