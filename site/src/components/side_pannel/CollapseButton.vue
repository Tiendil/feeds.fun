<template>
  <a
    href="#"
    class="ffun-page-header-link text-2xl align-middle flex-none pb-0"
    :title="title"
    @click.prevent="onClick"
    >
    <i v-if="globalSettings.showSidebar" class="ti ti-layout-sidebar-left-collapse"></i>
    <i v-else class="ti ti-layout-sidebar-left-expand"></i>
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

  function onClick() {
    globalSettings.showSidebar = !globalSettings.showSidebar;
  }

</script>
