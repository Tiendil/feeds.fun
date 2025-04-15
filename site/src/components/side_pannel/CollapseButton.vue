<template>
  <a
    href="#"
    class="ffun-page-header-link text-2xl align-middle flex-none pb-0 relative"
    :title="title"
    @click.prevent="onClick"
    >
    <i v-if="globalSettings.showSidebar" class="ti ti-layout-sidebar-left-collapse"></i>
    <i v-else class="ti ti-layout-sidebar-left-expand"></i>

    <span v-if="showPoint" class="absolute top-0 right-0 h-2 w-2 rounded-full bg-red-500 border border-white"></span>
  </a>
</template>

<script lang="ts" setup>
  import {ref, computed, useSlots, onMounted, watch, watchEffect} from "vue";
  import {useRouter, RouterLink, RouterView} from "vue-router";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useGlobalState} from "@/stores/globalState";
  import {useSupertokens} from "@/stores/supertokens";
  import * as events from "@/logic/events";
  import * as e from "@/logic/enums";
  import * as settings from "@/logic/settings";

  const globalSettings = useGlobalSettingsStore();

  const title = computed(() => {
    return globalSettings.showSidebar ? "Hide sidebar" : "Show sidebar";
  });

  const showPoint = computed(() => {
    return !globalSettings.showSidebar && globalSettings.showSidebarPoint;
  });

  function onClick() {
    globalSettings.showSidebar = !globalSettings.showSidebar;
  }

</script>
