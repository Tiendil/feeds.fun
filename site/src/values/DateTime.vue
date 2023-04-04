<template>
    {{ renderedDateTime }}
</template>

<script lang="ts" setup>
import { computed } from "vue";

const properties = defineProps<{
    value: Date;
}>();

const renderedDateTime = computed(() => {
    return properties.value.toLocaleString();
});
</script>

<style></style>
