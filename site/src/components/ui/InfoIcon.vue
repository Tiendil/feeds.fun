<template>
  <app-tooltip :text="properties.text">
    <button
      v-bind="$attrs"
      type="button"
      class="inline-flex cursor-help items-center justify-center rounded text-slate-500 transition-colors hover:text-black focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      :class="triggerSizeClasses[properties.size]"
      :aria-label="properties.text">
      <icon
        :class="iconSizeClasses[properties.size]"
        icon="info-square-filled"
        :size="properties.size" />
    </button>
  </app-tooltip>
</template>

<script lang="ts" setup>
  defineOptions({inheritAttrs: false});

  type InfoIconSize = "small" | "medium" | "large";

  const triggerSizeClasses: Record<InfoIconSize, string> = {
    small: "h-6 w-6",
    medium: "h-7 w-7",
    large: "h-8 w-8"
  };

  const iconSizeClasses: Record<InfoIconSize, string> = {
    small: "h-5 w-5",
    medium: "h-6 w-6",
    large: "h-7 w-7"
  };

  const properties = withDefaults(defineProps<{text: string; size?: InfoIconSize}>(), {size: "medium"});
</script>
