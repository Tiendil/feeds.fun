<template>
<side-panel-layout>

  <template #main-header>
    Collections
  </template>

  <feeds-collections/>

</side-panel-layout>
</template>

<script lang="ts" setup>
import { computed, ref, onUnmounted, watch } from "vue";
import { computedAsync } from "@vueuse/core";
import * as api from "@/logic/api";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";
import { useGlobalSettingsStore } from "@/stores/globalSettings";
import { useEntriesStore } from "@/stores/entries";

const globalSettings = useGlobalSettingsStore();

globalSettings.mainPanelMode = e.MainPanelMode.Collections;

</script>

<style></style>
