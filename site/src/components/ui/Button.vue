<template>
  <button
    :type="type"
    class="ui-button"
    :class="[buttonVariantClasses[properties.variant], buttonSizeClasses[properties.size]]">
    <slot />
  </button>
</template>

<script lang="ts" setup>
  type ButtonVariant = "primary" | "tonal" | "secondary" | "quiet" | "danger";
  type ButtonSize = "regular" | "compact";
  type ButtonType = "button" | "submit" | "reset";

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
      variant: ButtonVariant;
      size?: ButtonSize;
      type?: ButtonType;
    }>(),
    {size: "regular", type: "button"}
  );
</script>
