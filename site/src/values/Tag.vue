<template>
<div :class="classes"
     @click.prevent="onClick()">
  <span v-if="count">[{{count}}]</span>
  {{value}}
</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import { useEntriesStore } from "@/stores/entries";

const entriesStore = useEntriesStore();

const properties = defineProps<{value: string,
                                count?: number|null,
                                selected?: bool}>();

const emit = defineEmits(["tag:clicked"]);

const classes = computed(() => {
    return {
        "tag": true,
        "selected": properties.selected
    };
});

function onClick() {
    emit('tag:clicked', properties.value);
}

</script>

<style scoped>
.tag {
  display: inline-block;
  cursor: pointer;
  padding: 0.25rem;
  white-space: nowrap;
}

.tag.selected {
  background-color: #c1c1ff;
}

</style>
