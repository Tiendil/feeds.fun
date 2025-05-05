<template>
  <component
    :is="componentName"
    class="inline-block"
    v-bind="iconProperties" />
</template>

<script lang="ts" setup>
  import {computed} from "vue";
  import {
    IconArrowNarrowRight,
    IconArrowRight,
    IconPlus,
    IconDots,
    IconBrandReddit,
    IconBrandDiscord,
    IconBrandGithub,
    IconExternalLink,
    IconChevronsLeft,
    IconChevronsRight,
    IconLayoutSidebarLeftCollapse,
    IconLayoutSidebarLeftExpand,
    IconX,
    IconMoodSmile,
    IconMoodSad
  } from "@tabler/icons-vue";

  const iconMap = {
    reddit: IconBrandReddit,
    discord: IconBrandDiscord,
    github: IconBrandGithub,
    "arrow-narrow-right": IconArrowNarrowRight,
    "arrow-right": IconArrowRight,
    plus: IconPlus,
    dots: IconDots,
    "external-link": IconExternalLink,
    "chevrons-right": IconChevronsRight,
    "chevrons-left": IconChevronsLeft,
    "sidebar-left-collapse": IconLayoutSidebarLeftCollapse,
    "sidebar-left-expand": IconLayoutSidebarLeftExpand,
    x: IconX,
    "face-smile": IconMoodSmile,
    "face-sad": IconMoodSad
  } as const;

  type IconName = keyof typeof iconMap;

  const sizeMap = {
    small: 16,
    medium: 20,
    large: 24
  } as const;

  type IconSize = keyof typeof sizeMap;

  const properties = defineProps<{icon: IconName; size?: IconSize}>();

  const componentName = computed(() => {
    if (properties.icon in iconMap) {
      return iconMap[properties.icon];
    } else {
      throw new Error(`Icon ${properties.icon} not found`);
    }
  });

  const iconProperties = computed(() => {
    return {
      size: sizeMap[properties.size ?? "medium"]
    };
  });
</script>
