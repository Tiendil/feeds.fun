<template>
  <div class="">
    <score-selector
      class="inline-block mr-2"
      v-model="currentScore" />

    <a
      class="ffun-form-button"
      href="#"
      v-if="canCreateRule"
      @click.prevent="createOrUpdateRule()"
      >create rule</a
    >

    <p class="ffun-info-attention"> The news list will be updated right after you create a rule. </p>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import * as api from "@/logic/api";
  const properties = defineProps<{tags: string[]}>();

  const globalSettings = useGlobalSettingsStore();

  const emit = defineEmits(["rule-constructor:created"]);

  // fibonacci numbers
  const scores = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610];

  const currentScore = ref(1);

  const canCreateRule = computed(() => {
    return properties.tags.length > 0;
  });

  async function createOrUpdateRule() {
    await api.createOrUpdateRule({tags: properties.tags, score: currentScore.value});

    // this line leads to the reloading of news and any other data
    // not an elegant solution, but it works with the current API implementation
    // TODO: try to refactor to only update scores of news:
    //       - without reloading
    //       - maybe, without reordering too
    globalSettings.updateDataVersion();

    emit("rule-constructor:created");
  }
</script>
