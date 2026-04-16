<template>
  <div class="w-full overflow-hidden rounded border border-slate-300">
    <div class="aspect-video">
      <iframe
        class="h-full w-full"
        :src="embedUrl"
        :title="title"
        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
        allowfullscreen
        referrerpolicy="strict-origin-when-cross-origin" />
    </div>
  </div>
</template>

<script lang="ts" setup>
  import {computed} from "vue";

  const properties = withDefaults(
    defineProps<{
      videoId: string;
      title?: string;
    }>(),
    {
      title: "YouTube video"
    }
  );

  const embedUrl = computed(() => `https://www.youtube-nocookie.com/embed/${properties.videoId}`);
</script>
