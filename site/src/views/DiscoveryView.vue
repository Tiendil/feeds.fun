<template>
  <side-panel-layout :reload-button="false">
    <template #main-header> Discovery </template>

    <notifications
      :create-rule-help="false"
      :api-key="false"
      :collections-notification_="false"
      :collections-warning_="true" />

    <h2>Load feeds from an OPML file</h2>

    <div class="ffun-info-good">
      <p>
        <a
          href="https://en.wikipedia.org/wiki/OPML"
          target="_blank"
          >OPML</a
        >
        is a widely-used format for transferring news feed lists between platforms.
      </p>

      <p
        >Export your feeds from your old reader in OPML format and import them into our reader to seamlessly
        transition!</p
      >
    </div>

    <opml-upload />

    <h2>Search for a feed</h2>

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
