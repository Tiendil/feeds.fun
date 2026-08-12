<template>
  <div
    class="ui-notice ui-rich-text"
    :class="noticeToneClasses[properties.tone]">
    <slot />
  </div>
</template>

<script lang="ts" setup>
  type NoticeTone = "info" | "success" | "warning" | "danger";

  const noticeToneClasses: Record<NoticeTone, string> = {
    info: "ui-notice-info",
    success: "ui-notice-success",
    warning: "ui-notice-warning",
    danger: "ui-notice-danger"
  };

  const properties = defineProps<{tone: NoticeTone}>();
</script>
