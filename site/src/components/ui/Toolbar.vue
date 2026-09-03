<template>
  <div
    class="flex min-h-9 flex-wrap items-center gap-x-3 gap-y-1 rounded border border-slate-200 bg-slate-50 px-2 py-1">
    <div
      v-if="$slots.left"
      class="flex flex-wrap items-center gap-x-3 gap-y-1">
      <slot name="left" />
    </div>

    <div
      v-if="$slots.right"
      class="ml-auto flex flex-wrap items-center justify-end gap-x-3 gap-y-1">
      <slot name="right" />
    </div>
  </div>
</template>
