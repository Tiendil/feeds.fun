<template>
  <input
    type="file"
    class="ui-file-input"
    :disabled="disabled"
    @change="emit('change', $event)" />
</template>

<script lang="ts" setup>
  withDefaults(defineProps<{disabled?: boolean}>(), {disabled: false});

  const emit = defineEmits<{change: [event: Event]}>();
</script>
