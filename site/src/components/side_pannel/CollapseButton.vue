<template>
  <a
    href="#"
    class="ffun-page-header-link py-2 flex items-center justify-center"
    :title="title"
    @click.prevent="onClick">
    <icon
      v-if="showSidebar"
      icon="sidebar-left-collapse"
      size="large" />
    <icon
      v-else
      icon="sidebar-left-expand"
      size="large" />

    <span
      v-if="showPoint"
      class="absolute top-0 right-0 h-2 w-2 rounded-full bg-red-500 border border-white"></span>
  </a>
</template>

<script lang="ts" setup>
  import {ref, computed, useSlots, onMounted, watch, watchEffect, inject} from "vue";
  import {useRouter, RouterLink, RouterView} from "vue-router";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useGlobalState} from "@/stores/globalState";
  import {useSupertokens} from "@/stores/supertokens";
  import * as asserts from "@/logic/asserts";
  import * as events from "@/logic/events";
  import * as e from "@/logic/enums";
  import * as settings from "@/logic/settings";

  const globalSettings = useGlobalSettingsStore();

  const eventsView = inject<events.EventsViewName>("eventsViewName");

  asserts.defined(eventsView);

  const title = computed(() => {
    return globalSettings.showSidebar ? "Hide sidebar" : "Show sidebar";
  });

  const showSidebar = computed(() => {
    return globalSettings.showSidebar || !globalSettings.userSettingsPresent;
  });

  const showPoint = computed(() => {
    return !showSidebar.value && globalSettings.showSidebarPoint;
  });

  function onClick() {
    globalSettings.showSidebar = !globalSettings.showSidebar;

    asserts.defined(eventsView);

    events.sidebarStateChanged({
      view: eventsView,
      subEvent: globalSettings.showSidebar ? "show" : "hide",
      source: "top_sidebar_button"
    });
  }
</script>
