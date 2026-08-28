<template>
  <section class="ui-page-section">
    <h2 class="ui-page-section-title">
      {{ title }}
    </h2>

    <div
      v-if="$slots.description"
      class="ui-page-section-description">
      <slot name="description" />
    </div>

    <slot />
  </section>
</template>

<script lang="ts" setup>
  defineProps<{title: string}>();
</script>
