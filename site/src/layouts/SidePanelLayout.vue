<template>
  <div v-if="showGUI" class="ffun-side-panel-layout">
    <div
      v-if="showSidebar"
      class="ffun-side-panel">
      <div class="ffun-page-header pr-0 mr-0 flex min-w-full">
        <div class="ffun-page-header-title grow">
          <slot name="main-header"></slot>
        </div>

        <side-panel-collapse-button />
      </div>

      <hr />

      <ul class="ffun-side-panel-controls-list">
        <li v-if="hasSideMenuItem(1)">
          <slot name="side-menu-item-1"></slot>
        </li>

        <li v-if="hasSideMenuItem(2)">
          <slot name="side-menu-item-2"></slot>
        </li>

        <li v-if="hasSideMenuItem(3)">
          <slot name="side-menu-item-3"></slot>
        </li>

        <li v-if="hasSideMenuItem(4)">
          <slot name="side-menu-item-4"></slot>
        </li>

        <li v-if="hasSideMenuItem(5)">
          <slot name="side-menu-item-5"></slot>
        </li>
      </ul>

      <hr v-if="reloadButton" />

      <a
        class="ffun-side-panel-refresh-button short"
        v-if="reloadButton"
        href="#"
        @click="globalSettings.updateDataVersion()"
        >Refresh</a
      >

      <hr v-if="hasSideFooter" />

      <slot name="side-footer"></slot>
    </div>

    <div class="ffun-body-panel">
      <div class="ffun-page-header">
        <div class="ffun-page-header-left-block">
          <side-panel-collapse-button v-if="!showSidebar" />

          <page-header-home-button v-if="homeButton" />

          <template v-if="globalState.loginConfirmed">
            <template
              v-for="[mode, props] of e.MainPanelModeProperties"
              :key="mode">
              <template v-if="props.showInMenu">
                <a
                  v-if="globalSettings.mainPanelMode !== mode"
                  :href="router.resolve({name: mode, params: {}}).href"
                  class="ffun-page-header-link"
                  @click.prevent="router.push({name: mode, params: {}})">
                  {{ props.text }}
                </a>

                <span
                  class="ffun-page-header-link-active"
                  v-else
                  >{{ props.text }}</span
                >
              </template>
            </template>
          </template>

          <page-header-external-links/>
        </div>

        <div class="ffun-page-header-right-block">
          <a
            v-if="globalState.loginConfirmed && !globalState.isSingleUserMode"
            href="#"
            class="ffun-page-header-link"
            @click.prevent="globalState.logout()"
            >logout</a
          >

          <span
            v-if="globalState.isSingleUserMode"
            href="#"
            class="ffun-page-header-link-disabled"
            >single-user mode</span
          >
        </div>
      </div>

      <hr class="mx-4 my-2 border-slate-400" />

      <main class="mb-4 px-4 min-h-screen">
        <slot></slot>
      </main>

      <footer>
        <slot name="main-footer"></slot>
      </footer>
    </div>
  </div>

  <page-footer v-if="showGUI" />
</template>

<script lang="ts" setup>
  import {ref, computed, useSlots, onMounted, watch, watchEffect} from "vue";
  import {useRouter} from "vue-router";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useGlobalState} from "@/stores/globalState";
  import * as events from "@/logic/events";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import * as settings from "@/logic/settings";

  const globalSettings = useGlobalSettingsStore();
  const globalState = useGlobalState();

  const router = useRouter();
  const slots = useSlots();

  const properties = withDefaults(
    defineProps<{reloadButton?: boolean; loginRequired?: boolean; homeButton?: boolean}>(),
    {
      reloadButton: true,
      loginRequired: true,
      homeButton: false
    }
  );

  const hasSideFooter = computed(() => {
    return !!slots["side-footer"];
  });

  function hasSideMenuItem(index: number) {
    return !!slots[`side-menu-item-${index}`];
  }

  const showSidebar = computed(() => {
    return globalSettings.showSidebar || !globalSettings.userSettingsPresent;
  });

  const showGUI = computed(() => {
    return globalState.loginConfirmed || !properties.loginRequired;
  });

  watchEffect(() => {
    if (!properties.loginRequired) {
      return;
    }

    if (globalState.logoutConfirmed) {
      // Redirect to login page in case the user is not logged in.
      // We redirect to login instead of the main page to be consisten
      // with default API behavior on redirection in case of getting 401 status.
      api.redirectToLogin();
    }
  });
</script>
