<template>
  <h2>
    Discovery
  </h2>
  <opml-upload/>
  <hr/>
  <discovery-form/>
</template>

<script lang="ts" setup>
import { computed, ref, onUnmounted, watch } from "vue";
import { computedAsync } from "@vueuse/core";
import { useGlobalSettingsStore } from "@/stores/globalSettings";
import * as api from "@/logic/api";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";

const globalSettings = useGlobalSettingsStore();

globalSettings.mainPanelMode = e.MainPanelMode.Discovery;

</script>

<style></style>
