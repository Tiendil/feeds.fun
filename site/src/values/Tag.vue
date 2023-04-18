<template>
    <div :class="classes" @click.prevent="switchSelection()">{{value}}</div>
</template>

<script lang="ts" setup>
    import { computed, ref } from "vue";

const properties = defineProps<{value: string}>();

const emit = defineEmits(["tag:selected", "tag:deselected"]);

const selected = ref(false);

const classes = computed(() => {
    return {
        "tag": true,
        "selected": selected.value
    };
});

function switchSelection() {
    selected.value = !selected.value;

    if (selected.value) {
        emit('tag:selected', properties.value);
    } else {
        emit('tag:deselected', properties.value);
    }
}


</script>

<style scoped>
.tag {
  display: inline-block;
  cursor: pointer;
  padding: 0.25rem;
}

.tag.selected {
  background-color: #eee;
}

</style>
