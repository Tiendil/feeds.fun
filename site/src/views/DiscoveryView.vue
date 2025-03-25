<template>
  <side-panel-layout :reload-button="false">
    <template #main-header> Discovery </template>

    <notifications
      :create-rule-help="false"
      :api-key="false"
      :collections-notification_="false"
      :collections-warning_="true" />

    <h3>Load feeds from an OPML file</h3>

    <div class="ffun-info-common">
      <p>
        <external-url
          url="https://en.wikipedia.org/wiki/OPML"
          text="OPML" />
        is a widely-used format for transferring news feed lists between platforms.
      </p>

      <p
        >Export your feeds from your old reader in OPML format and import them into Feeds Fun to seamlessly
        transition.</p
      >
    </div>

    <opml-upload class="mt-4" />

    <h3>Search for a feed</h3>

    <discovery-form />
  </side-panel-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch, provide} from "vue";
  import {computedAsync} from "@vueuse/core";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import * as api from "@/logic/api";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";

const globalSettings = useGlobalSettingsStore();

provide("eventsViewName", "discovery");

  globalSettings.mainPanelMode = e.MainPanelMode.Discovery;
</script>

<style></style>
