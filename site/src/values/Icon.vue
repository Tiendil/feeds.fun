<template>
  <component
    :is="componentName"
    class="inline-block align-middle"
    v-bind="iconProperties"
    />
</template>

<script lang="ts" setup>
  import {computed} from "vue";
import {IconArrowNarrowRight, IconArrowRight, IconPlus, IconDots, IconBrandReddit, IconBrandDiscord, IconBrandGithub, IconExternalLink} from "@tabler/icons-vue";

const properties = defineProps<{icon: string,
                                size?: string}>();

const iconMap = {
  reddit: IconBrandReddit,
  discord: IconBrandDiscord,
  github: IconBrandGithub,
  'arrow-narrow-right': IconArrowNarrowRight,
  'arrow-right': IconArrowRight,
  plus: IconPlus,
  dots: IconDots,
  'external-link': IconExternalLink,
};

const sizeMap = {
  small: 16,
  medium: 20,
  large: 24,
};

const componentName = computed(() => {
  if (properties.icon in iconMap) {
    return iconMap[properties.icon];
  } else {
    throw new Error(`Icon ${properties.icon} not found`);
  }
});

const iconProperties = computed(() => {
  return {
    size: sizeMap[properties.size] || sizeMap.medium,
    // "stroke-width": 2,
  };
});

</script>
