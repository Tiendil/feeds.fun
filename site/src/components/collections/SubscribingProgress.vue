<template>
  <ui-notice
    v-if="loading"
    tone="info"
    class="mt-4">
    <p>Subscribing…</p>
  </ui-notice>

  <ui-notice
    v-if="loaded"
    tone="success"
    class="mt-4"
    ><p>Feeds added!</p>
  </ui-notice>
  <ui-notice
    v-if="error"
    tone="danger"
    class="mt-4"
    ><p>Unknown error occurred! Please, try later.</p>
  </ui-notice>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useEntriesStore} from "@/stores/entries";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useCollectionsStore} from "@/stores/collections";

  const properties = defineProps<{
    loading: boolean;
    loaded: boolean;
    error: boolean;
  }>();
</script>

<style scoped></style>
