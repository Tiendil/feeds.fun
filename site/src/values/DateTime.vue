<template>
    {{ text }}
</template>

<script lang="ts" setup>
import { computed } from "vue";
import * as u from "@/logic/utils";

const properties = defineProps<{
    value: Date;
    reversed: boolean;
}>();

const text = computed(() => {
    if (properties.value === null) {
        return "—";
    }

    if (!properties.reversed) {
        return properties.value.toLocaleString();
    } else {
        return u.timeSince(properties.value);
    }
});
</script>

<style></style>
