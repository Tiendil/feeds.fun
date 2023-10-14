<template>
  <div class="">
    <p>Select tags to score news by them.</p>

    <template
      v-for="tag of tags"
      :key="tag">
      <ffun-tag
        :uid="tag"
        mode="required" />&nbsp;
    </template>

    <br />

    <score-selector class="inline-block mr-2" v-model="currentScore" />

    <a
      class="ffun-form-button"
      href="#"
      v-if="canCreateRule"
      @click.prevent="createOrUpdateRule()"
      >create rule</a
    >
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import * as api from "@/logic/api";
  const properties = defineProps<{tags: string[]}>();

  const emit = defineEmits(["rule-constructor:created"]);

  // fibonacci numbers
  const scores = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610];

  const currentScore = ref(1);

  const canCreateRule = computed(() => {
    return properties.tags.length > 0;
  });

  async function createOrUpdateRule() {
    await api.createOrUpdateRule({tags: properties.tags, score: currentScore.value});
    emit("rule-constructor:created");
  }
</script>
