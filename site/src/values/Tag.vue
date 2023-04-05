<template>
  {{value}}
</template>

<script lang="ts" setup>
import { computed } from "vue";

const properties = defineProps<{value: string}>();

const name = computed(() => {
    return properties.value;
});

</script>

<style></style>
