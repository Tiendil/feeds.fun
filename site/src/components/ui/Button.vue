<template>
  <app-tooltip :text="tooltip">
    <button
      v-bind="$attrs"
      :type="type"
      class="ui-button"
      :class="[buttonVariantClasses[properties.variant], buttonSizeClasses[properties.size]]">
      <slot />
    </button>
  </app-tooltip>
</template>

<script lang="ts" setup>
  defineOptions({inheritAttrs: false});

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
      tooltip?: string;
    }>(),
    {size: "regular", type: "button", tooltip: ""}
  );
</script>
