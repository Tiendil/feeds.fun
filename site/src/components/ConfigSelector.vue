<template>

    <select @change="updateProperty($event)">
      <option v-for="[value, props] of values"
              :value="value"
              :selected="value === property">
        {{props.text}}
      </option>
    </select>

</template>

<script lang="ts" setup>
import * as e from "@/logic/enums";

const properties = defineProps<{values: any,
                                property: string}>();

const emit = defineEmits(["update:property"]);


function updateProperty(event) {
    emit('update:property', event.target.value);
}

</script>

<style></style>
