<template>
  <section class="border-t border-slate-200 py-5 first:border-t-0 first:pt-0">
    <h2 class="mb-2 mt-0 text-xl font-semibold leading-relaxed text-slate-900">
      {{ title }}
    </h2>

    <div
      v-if="$slots.description"
      class="mb-4 max-w-4xl space-y-2 text-base leading-relaxed text-slate-700">
      <slot name="description" />
    </div>

    <slot />
  </section>
</template>

<script lang="ts" setup>
  defineProps<{title: string}>();
</script>
