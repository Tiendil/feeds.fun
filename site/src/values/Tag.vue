<template>
<div :class="classes"
     :title="tooltip"
     @click.prevent="onClick()">

  <slot name="start">
  </slot>

  <span v-if="countMode == 'prefix'">[{{count}}]</span>

  {{value}}
</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import { useEntriesStore } from "@/stores/entries";

const entriesStore = useEntriesStore();

const properties = defineProps<{value: string,
                                count?: number|null,
                                countMode?: string|null,
                                mode?: string|null}>();

const emit = defineEmits(["tag:clicked"]);

const classes = computed(() => {
    const result = {
        "tag": true
    };

    if (properties.mode) {
        result[properties.mode] = true;
    }

    return result;
});

function onClick() {
    emit('tag:clicked', properties.value);
}

const tooltip = computed(() => {
    if (properties.countMode == 'tooltip' && properties.count) {
        return `articles with the tag: ${properties.count}`;
    }
    return '';
});

</script>

<style scoped>
.tag {
  display: inline-block;
  cursor: pointer;
  padding: 0.25rem;
  white-space: nowrap;
}

.tag.selected {
  background-color: #ccccff;
}

.tag.required {
  background-color: #ccffcc;
}

.tag.excluded {
  background-color: #ffcccc;
}

</style>
