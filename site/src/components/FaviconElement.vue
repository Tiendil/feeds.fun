<template>
  <img
    :src="faviconUrl"
    @error="handleFaviconError" />
</template>

<script setup lang="ts">
  import * as utils from "@/logic/utils";
  import {computed, ref} from "vue";

  const properties = defineProps<{url: string}>();

  const noFavicon = ref(false);

  function handleFaviconError() {
    noFavicon.value = true;
  }

  const faviconUrl = computed(() => {
    if (noFavicon.value) {
      return "/no-favicon.ico";
    }

    const url = utils.faviconForUrl(properties.url);

    if (url == null) {
      return "/no-favicon.ico";
    }

    return url;
  });
</script>

<style scoped></style>
