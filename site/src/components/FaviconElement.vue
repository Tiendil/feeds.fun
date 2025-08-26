<template>
  <img
    :src="faviconUrl"
    @error="handleFaviconError" />
</template>

<script setup lang="ts">
  import * as utils from "@/logic/utils";
  import noFaviconImage from "@/assets/no-favicon.ico";
  import {computed, ref} from "vue";

  const properties = defineProps<{url: string}>();

  const noFavicon = ref(false);

  function handleFaviconError() {
    noFavicon.value = true;
  }

  const faviconUrl = computed(() => {
    if (noFavicon.value) {
      return noFaviconImage;
    }

    const url = utils.faviconForUrl(properties.url);

    if (url == null) {
      return noFaviconImage;
    }

    return url;
  });
</script>

<style scoped></style>
