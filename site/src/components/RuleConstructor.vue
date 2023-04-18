<template>
<div class="score-rule-constructor">

<p>
Select tags to score news by them.
</p>

  <template v-for="tag of tags"
            :key="tag">
    <value-tag :value="tag"
               :selected="true"/>&nbsp;
</template>

<br/>

    <select v-model="currentScore">
      <option v-for="score of scores"
              :value="score"
              :selected="currentScore === score">
        {{score}}
      </option>
    </select>

    &nbsp;

  <a href="#" v-if="canCreateRule" @click.prevent="createRule()">create rule</a>

</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import * as api from "@/logic/api";
const properties = defineProps<{ tags: string[]}>();

const emit = defineEmits(["rule-constructor:created"]);

// fibonacci numbers
const scores = [1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610];

const currentScore = ref(1);

const canCreateRule = computed(() => {
    return properties.tags.length > 0;
});

async function createRule() {
    await api.createRule({tags: properties.tags, score: currentScore.value});
    emit("rule-constructor:created");
}
</script>

<style scoped>
.score-rule-constructor {
    padding: 0.25rem;
    margin: 0.25rem;
    border: 1px solid #ccc;
}
</style>
