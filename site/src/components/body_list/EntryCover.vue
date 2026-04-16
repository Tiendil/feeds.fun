<template>
  <div v-if="youtubeVideoId !== null">
    <integrations-you-tube
      :video-id="youtubeVideoId"
      :title="reference.title ?? 'YouTube video'" />
  </div>

  <img
    v-else-if="isImage"
    ref="imageElement"
    :class="imageClass"
    :src="reference.url"
    :style="imageStyle"
    :alt="reference.title ?? 'Entry cover'" />
</template>

<script lang="ts" setup>
  import {computed, useTemplateRef} from "vue";
  import {useElementSize} from "@vueuse/core";
  import * as e from "@/logic/enums";
  import type * as t from "@/logic/types";

  const properties = defineProps<{
    reference: t.Reference;
    containerWidth?: number;
  }>();

  const imageElement = useTemplateRef("imageElement");
  const {width: imageWidth} = useElementSize(imageElement);

  const youtubeVideoId = computed(() => {
    if (properties.reference.semantics !== e.ReferenceSemantics.Video) {
      return null;
    }

    return properties.reference.youtubeId();
  });

  const isImage = computed(() => properties.reference.semantics === e.ReferenceSemantics.Image);
  const shouldWrapImage = computed(() => {
    if (!isImage.value) {
      return false;
    }

    if (properties.containerWidth === undefined || properties.containerWidth <= 0) {
      return false;
    }

    if (imageWidth.value <= 0) {
      return false;
    }

    return imageWidth.value <= properties.containerWidth / 2;
  });

  const imageClass = computed(() => {
    if (shouldWrapImage.value) {
      return "float-left mb-2 mr-4 block max-h-[32rem] max-w-full rounded border border-slate-300 object-cover";
    }

    return "mx-auto block max-h-[32rem] max-w-full rounded border border-slate-300 object-cover";
  });

  const imageStyle = computed(() => {
    if (properties.reference.semantics !== e.ReferenceSemantics.Image) {
      return null;
    }

    if (properties.reference.width === null || properties.reference.width <= 0) {
      return null;
    }

    return {maxWidth: `${properties.reference.width}px`};
  });
</script>
