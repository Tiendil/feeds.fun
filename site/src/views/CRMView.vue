<template>
  <wide-layout>
    <div class="ffun-page-header">
      <div class="ffun-page-header-center-block">
        <page-header-home-button />
        <page-header-external-links :show-api="false" />
      </div>
    </div>

    <hr />

    <main-block>
      <h1 class="m-0 text-5xl">Feeds Fun</h1>
      <p class="mt-2 text-2xl">Transparent Personalized News</p>
    </main-block>

    <hr />

    <main-block>
      <div
        v-html="actualContent"
        class="prose max-w-none" />
    </main-block>
  </wide-layout>
</template>

<script lang="ts" setup>
  import {computed, provide} from "vue";

  const properties = defineProps<{content: string | null; kind: string}>();

  provide("eventsViewName", properties.kind);

  const actualContent = computed(() => {
    if (properties.content === null) {
      return "You MUST define a content for this page in case you host public version of Feeds Fun.";
    }

    return properties.content;
  });
</script>
