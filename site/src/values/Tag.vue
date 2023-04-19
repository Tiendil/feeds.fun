<template>
    <div :class="classes" @click.prevent="onClick()">{{value}}</div>
</template>

<script lang="ts" setup>
    import { computed, ref } from "vue";

const properties = defineProps<{value: string,
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
}

.tag.selected {
  background-color: #eee;
}

</style>
