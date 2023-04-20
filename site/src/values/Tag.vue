<template>
<div :class="classes"
     @click.prevent="onClick()">
    [{{count}}] {{value}}
</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import { useEntriesStore } from "@/stores/entries";

const entriesStore = useEntriesStore();

const properties = defineProps<{value: string,
                                selected?: bool}>();

const emit = defineEmits(["tag:clicked"]);

const classes = computed(() => {
    return {
        "tag": true,
        "selected": properties.selected
    };
});

const count = computed(() => {
    return entriesStore.reportTagsCount[properties.value];
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
