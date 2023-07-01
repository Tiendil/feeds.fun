<template>
<side-panel-layout :reload-button="false">

  <template #main-header>
    Settings
  </template>

  !
  {{globalSettings.userSettings}}
  !

</side-panel-layout>
</template>

<script lang="ts" setup>
import { computed, ref, onUnmounted, watch } from "vue";
import { computedAsync } from "@vueuse/core";
import * as api from "@/logic/api";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";
import { useGlobalSettingsStore } from "@/stores/globalSettings";

const globalSettings = useGlobalSettingsStore();

globalSettings.mainPanelMode = e.MainPanelMode.Settings;

</script>

<style></style>
