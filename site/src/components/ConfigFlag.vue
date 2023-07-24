<template>
  <a
    v-if="flag"
    href="#"
    @click="emit('update:flag', false)"
    >{{ onText }}</a
  >
  <a
    v-if="!flag"
    href="#"
    @click="emit('update:flag', true)"
    >{{ offText }}</a
  >
</template>

<script setup lang="ts">
  defineProps<{flag: boolean; onText: string; offText: string}>();

  const emit = defineEmits(["update:flag"]);
</script>

<style scoped></style>
