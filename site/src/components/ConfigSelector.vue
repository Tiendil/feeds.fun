<template>
  <select
    class="ffun-input"
    @change="updateProperty($event)">
    <option
      v-if="!propertyDefined"
      value=""
      selected>
    </option>

    <option
      v-for="[value, props] of values"
      :value="value"
      :selected="value === property && propertyDefined">
      {{ props.text }}
    </option>
  </select>
</template>

<script lang="ts" setup>
  import {computed} from "vue";
  import * as e from "@/logic/enums";

  const properties = defineProps<{values: any; property: string | null}>();

  const propertyDefined = computed(() => properties.property !== null && properties.property !== undefined);

  const emit = defineEmits(["update:property"]);

  function updateProperty(event: Event) {
    const target = event.target as HTMLSelectElement;
    emit("update:property", target.value);
  }
</script>

<style></style>
