<template>
  <button
    :type="type"
    class="inline-flex items-center justify-center rounded border text-sm font-medium leading-5 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-1 disabled:cursor-not-allowed disabled:opacity-50"
    :class="variantClasses[variant]">
    <slot />
  </button>
</template>

<script lang="ts" setup>
  type ButtonVariant = "primary" | "secondary" | "quiet" | "danger";
  type ButtonType = "button" | "submit" | "reset";

  withDefaults(
    defineProps<{
      variant: ButtonVariant;
      type?: ButtonType;
    }>(),
    {type: "button"}
  );

  const variantClasses: Record<ButtonVariant, string> = {
    primary:
      "border-blue-600 bg-blue-600 px-3 py-1.5 text-white hover:border-blue-700 hover:bg-blue-700 focus:ring-blue-500",
    secondary:
      "border-slate-300 bg-white px-3 py-1.5 text-slate-800 hover:border-slate-400 hover:bg-slate-50 focus:ring-slate-400",
    quiet:
      "border-transparent bg-transparent px-1 py-1 text-blue-700 hover:bg-slate-100 hover:text-blue-800 focus:ring-blue-500",
    danger: "border-red-600 bg-red-600 px-3 py-1.5 text-white hover:border-red-700 hover:bg-red-700 focus:ring-red-500"
  };
</script>
