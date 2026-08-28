<template>
  <div
    class="ui-advisory ui-rich-text"
    :class="guidanceToneClasses[properties.tone]">
    <slot />
  </div>
</template>

<script lang="ts" setup>
  type GuidanceTone = "neutral" | "positive";

  const guidanceToneClasses: Record<GuidanceTone, string> = {
    neutral: "ui-guidance-panel-neutral",
    positive: "ui-guidance-panel-positive"
  };

  const properties = withDefaults(defineProps<{tone?: GuidanceTone}>(), {tone: "neutral"});
</script>
