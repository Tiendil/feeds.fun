<template>
  <a
    :href="href"
    :target="target"
    class="ui-button"
    :class="[buttonVariantClasses[properties.variant], buttonSizeClasses[properties.size]]">
    <slot />
  </a>
</template>

<script lang="ts" setup>
  type ButtonVariant = "primary" | "tonal" | "secondary" | "quiet" | "danger";
  type ButtonSize = "regular" | "compact";

  const buttonVariantClasses: Record<ButtonVariant, string> = {
    primary: "ui-button-primary",
    tonal: "ui-button-tonal",
    secondary: "ui-button-secondary",
    quiet: "ui-button-quiet",
    danger: "ui-button-danger"
  };

  const buttonSizeClasses: Record<ButtonSize, string> = {
    regular: "ui-button-regular",
    compact: "ui-button-compact"
  };

  const properties = withDefaults(
    defineProps<{
      href: string;
      variant: ButtonVariant;
      size?: ButtonSize;
      target?: string;
    }>(),
    {size: "regular"}
  );
</script>
