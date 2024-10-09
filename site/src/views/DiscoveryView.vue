<template>
  <side-panel-layout :reload-button="false">
    <template #main-header> Discovery </template>

    <notifications
      :create-rule-help="false"
      :api-key="false"
      :collections-notification_="false"
      :collections-warning_="true"
      />

    <h2>Lood feeds from an OPML file</h2>

    <opml-upload />

    <h2>Search for a feed</h2>

    <div class="ffun-info-attention">
      <p> The discovery feature is experimental and might not work on all websites. </p>

      <p> If we can’t find a feed for a site, try finding the feed's URL manually, then enter it in the form. </p>
    </div>

    <discovery-form />
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch} from "vue";
  import {computedAsync} from "@vueuse/core";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import * as api from "@/logic/api";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";

  const globalSettings = useGlobalSettingsStore();

  globalSettings.mainPanelMode = e.MainPanelMode.Discovery;
</script>

<style></style>
