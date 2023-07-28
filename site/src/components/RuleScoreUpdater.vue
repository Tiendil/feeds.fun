<template>
  <div>
    <score-selector
      :modelValue="currentScore"
      @input="updateSelected" />
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import * as api from "@/logic/api";
  import type * as t from "@/logic/types";

  const properties = defineProps<{
    score: number;
    ruleId: t.RuleId;
    tags: string[];
  }>();

  const currentScore = ref(properties.score);

  async function updateSelected(event: Event) {
    const target = event.target as HTMLInputElement;
    const newScore = Number(target.value);
    await api.updateRule({
      id: properties.ruleId,
      score: newScore,
      tags: properties.tags
    });
  }
</script>

<style scoped></style>
