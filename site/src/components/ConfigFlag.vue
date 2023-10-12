<template>
<button
  class="ffun-form-button"
  @click="emit('update:flag', !flag)">
  <span v-if="flag">{{ offText }}</span>
  <span v-else>{{ onText }}</span>
</button>
</template>

<script setup lang="ts">
  defineProps<{flag: boolean; onText: string; offText: string}>();

const emit = defineEmits(["update:flag"]);

</script>
