<template>
    {{feedId}}
</template>

<script lang="ts" setup>
import { computed } from "vue";
import * as t from "@/logic/types";

const properties = defineProps<{ value: t.FeedId }>();

const feedId = computed(() => {
    if (properties.value == null) {
        return `—`;
    }

    const id = properties.value;

    return id.slice(0, 3) + "***" + id.slice(-3);
});

</script>

<style></style>
