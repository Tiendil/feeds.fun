<template>
  <select
    class="ffun-input"
    @change="updateProperty($event)">
    <option
      v-for="[value, props] of values"
      :value="value"
      :selected="value === property">
      {{ props.text }}
    </option>
  </select>
</template>

<script lang="ts" setup>
  import * as e from "@/logic/enums";

  const properties = defineProps<{values: any; property: string}>();

  const emit = defineEmits(["update:property"]);

  function updateProperty(event: Event) {
    const target = event.target as HTMLSelectElement;
    emit("update:property", target.value);
  }
</script>

<style></style>
