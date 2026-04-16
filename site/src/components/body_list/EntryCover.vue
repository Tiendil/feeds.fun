<template>
  <div v-if="youtubeVideoId !== null">
    <integrations-you-tube
      :video-id="youtubeVideoId"
      :title="reference.title ?? 'YouTube video'" />
  </div>

  <img
    v-else-if="isImage"
    class="block max-h-[32rem] w-full rounded border border-slate-300 object-cover"
    :src="reference.url"
    :style="imageStyle"
    :alt="reference.title ?? 'Entry cover'" />
</template>

<script lang="ts" setup>
  import {computed} from "vue";
  import * as e from "@/logic/enums";
  import type * as t from "@/logic/types";

  const properties = defineProps<{
    reference: t.Reference;
  }>();

  const youtubeVideoId = computed(() => {
    if (properties.reference.semantics !== e.ReferenceSemantics.Video) {
      return null;
    }

    return properties.reference.youtubeId();
  });

  const isImage = computed(() => properties.reference.semantics === e.ReferenceSemantics.Image);

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
