<template>
<div class="container">

  <div style="flex-shrink: 0; width: 5rem; left-padding: 0.25rem;">
    <a href="#" @click.prevent="unsubscribe()">
      unsubscribe
    </a>
  </div>

  <div style="flex-shrink: 0; width: 1rem; left-padding: 0.25rem;">
    <value-date-time :value="feed.loadedAt" :reversed="true"/>
  </div>

  <div style="flex-shrink: 0; width: 2rem; text-align: right; padding-right: 0.25rem;">
    <span v-if="isOk"
          title="everything is ok"
          class="state-ok">ok</span>
    <span v-else
          :title="feed.lastError"
          class="state-error">⚠</span>
  </div>

  <div style="flex-grow: 1;">
    <value-url :value="feed.url"
               :text="purifiedTitle"/>
    <template v-if="globalSettings.showFeedsDescriptions">
      <br/>
      <div v-html="purifiedDescription"/>
    </template>
  </div>

</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";
import * as api from "@/logic/api";
import { computedAsync } from "@vueuse/core";
import DOMPurify from "dompurify";
import { useGlobalSettingsStore } from "@/stores/globalSettings";

const globalSettings = useGlobalSettingsStore();

const properties = defineProps<{ feed: t.Feed}>();

const purifiedTitle = computed(() => {
    if (properties.feed.title === null) {
        return "";
    }

    let title = DOMPurify.sanitize(properties.feed.title, {ALLOWED_TAGS: []});

    if (title.length === 0) {
        return null;
    }

    return title;
});

const purifiedDescription = computed(() => {
    if (properties.feed.description === null) {
        return "";
    }
    return DOMPurify.sanitize(properties.feed.description);
});

const isOk = computed(() => {
    return properties.feed.state === "loaded";
});

async function unsubscribe() {
    await api.unsubscribe({feedId: properties.feed.id});
}

</script>

<style scoped>
  .container {
      display: flex;
  }

  .container :deep(img) {
     max-width: 100%;
     height: auto;
  }

  .state-ok {
    color: green;
    cursor: default;
}

  .state-error {
      color: red;
      cursor: default;
  }
</style>
