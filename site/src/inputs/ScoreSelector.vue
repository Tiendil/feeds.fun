<template>
  <div>
    <select
      :value="modelValue"
      @input="updateSelected">
      <option
        v-for="score of scores"
        :value="score"
        :selected="modelValue === score">
        {{ score }}
      </option>
    </select>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import * as api from "@/logic/api";

  const properties = withDefaults(defineProps<{scores?: number[]; modelValue: number}>(), {
    scores: () => [
      1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233, 377, 610, -1, -2, -3, -5, -8, -13, -21, -34, -55, -89, -144, -233,
      -377, -610
    ],
    modelValue: 1
  });

  const emit = defineEmits(["update:modelValue"]);

  function updateSelected(event: Event) {
    const target = event.target as HTMLSelectElement;

    const newScore = Number(target.value);
    emit("update:modelValue", newScore);
  }
</script>

<style scoped></style>
