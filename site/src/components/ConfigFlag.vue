<template>
  <button
    class="ffun-config-flag"
    @click="emit('update:flag', !flag)">
    <span v-if="!flagDefined">&nbsp;</span>
    <span v-else-if="flag">{{ onText }}</span>
    <span v-else>{{ offText }}</span>
  </button>
</template>

<script setup lang="ts">
  import {computed} from "vue";

  const properties = defineProps<{flag: boolean | null; onText: string; offText: string}>();

  const flagDefined = computed(() => properties.flag !== null && properties.flag !== undefined);

  const emit = defineEmits(["update:flag"]);
</script>
