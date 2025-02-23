<template>
  <div v-if="loading"
       class="ffun-info-waiting mt-4">
    <p
      >Subscribing…</p
                     >
  </div>

    <div
      v-if="loaded"
      class="ffun-info-good mt-4"
      ><p>Feeds added!</p
    >
</div>
    <div
      v-if="error"
      class="ffun-info-bad mt-4"
      ><p>Unknown error occurred! Please, try later.</p
    >
  </div>
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
