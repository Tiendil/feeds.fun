<template>
  <div
    class="score"
    @click.prevent="onClick()">
    {{ value }}
  </div>
</template>

<script lang="ts" setup>
  import * as api from "@/logic/api";
  import type * as t from "@/logic/types";
  import {useTagsStore} from "@/stores/tags";

  const tagsStore = useTagsStore();

  const properties = defineProps<{value: number; entryId: t.EntryId}>();

  async function onClick() {
    const rules = await api.getScoreDetails({entryId: properties.entryId});

    if (rules.length === 0) {
      alert("No rules for this news");
      return;
    }

    rules.sort((a, b) => b.score - a.score);

    const strings = [];

    for (const rule of rules) {
      const tags = [];

      for (const tagId of rule.tags) {
        const tagInfo = tagsStore.tags[tagId];
        if (tagInfo) {
          tags.push(tagInfo.name);
        } else {
          tags.push(tagId);
        }
      }

      strings.push(rule.score.toString().padStart(2, " ") + " — " + tags.join(", "));
    }

    alert(strings.join("\n"));
  }
</script>

<style scoped>
  .score {
    display: inline-block;
    cursor: pointer;
    padding: 0.1rem;
    background-color: #c1c1ff;
  }
</style>
