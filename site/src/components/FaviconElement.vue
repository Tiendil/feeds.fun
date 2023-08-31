<template>
  <img :src="faviconUrl"
       @error="handleFaviconError"/>
</template>

<script setup lang="ts">
  import * as utils from "@/logic/utils";
  import {computed, ref} from "vue";

  const properties = defineProps<{url: str}>();

const noFavicon = ref(false);

function handleFaviconError() {
  noFavicon.value = true;
  }

const faviconUrl = computed(() => {
  if (noFavicon.value) {
    return '/no-favicon.ico'
  }
  return utils.faviconForUrl(properties.url);
});
</script>

<style scoped></style>
