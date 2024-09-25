<template>
  <div>
    <p
      v-if="loading"
      class="ffun-info-attention"
      >Subscribing...</p
    >

    <p
      v-if="loaded"
      class="ffun-info-good"
      >Feeds added!</p
    >

    <p
      v-if="error"
      class="ffun-info-bad"
      >Unknown error occurred! Please, try later.</p
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
