<template>

    <select @change="updateProperty($event)">
      <option v-for="[value, text] of texts"
              :value="value"
              :selected="value === property">
        {{text}}
      </option>
    </select>

</template>

<script lang="ts" setup>
import * as e from "@/logic/enums";

const properties = defineProps<{options: e.AnyEnum,
                                texts: e.AnyEnumText,
                                property: string}>();

const emit = defineEmits(["update:property"]);


function updateProperty(event) {
    // properties.property = event.target.value;

    emit('update:property', event.target.value);
}

</script>

<style></style>
