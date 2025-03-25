<template>
  <side-panel-layout :reload-button="false">
    <template #main-header> Collections </template>

    <div class="ffun-info-common">
      <p>We've prepared thematic collections just for you.</p>
      <p>News from collections are always tagged, ensuring you get the full power of Feeds Fun!</p>
    </div>

    <div
      v-for="collectionId in collections.collectionsOrder"
      :key="collectionId"
      class="collection-block pb-4">
      <collections-detailed-item :collectionId="collectionId" />
    </div>
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch, provide} from "vue";
  import {computedAsync} from "@vueuse/core";
  import * as api from "@/logic/api";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useCollectionsStore} from "@/stores/collections";

  const globalSettings = useGlobalSettingsStore();

const collections = useCollectionsStore();

provide("eventsViewName", "collections");

  globalSettings.mainPanelMode = e.MainPanelMode.Collections;
</script>

<style scoped>
  .collection-block:not(:last-child) {
    border-bottom-width: 1px;
  }
</style>
