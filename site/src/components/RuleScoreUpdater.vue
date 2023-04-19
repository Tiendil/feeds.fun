<template>
<div>
    <score-selector :modelValue="currentScore" @input="updateSelected"/>
</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import * as api from "@/logic/api";
import * as t from "@/logic/types";

const properties = defineProps<{ score: number,
                                 ruleId: t.RuleId,
                                 tags: string[]}>();

const currentScore = ref(properties.score);

async function updateSelected(event) {
    const newScore = Number(event.target.value);
    await api.updateRule({id: properties.ruleId, score: newScore, tags: properties.tags});
}
</script>

<style scoped>
</style>
