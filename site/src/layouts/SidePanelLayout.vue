<template>
<div class="ffun-side-panel-layout">
  <div v-if="!globalSettings.showSidebar" class="ffun-side-panel-collapsed">
    <div class="ffun-page-header px-0 mx-0 flex min-w-full">
      <side-panel-collapse-button/>
    </div>
  </div>
    <div v-if="globalSettings.showSidebar" class="ffun-side-panel">
      <div class="ffun-page-header pr-0 mr-0 flex min-w-full">
        <div class="ffun-page-header-title grow">
          <slot name="main-header"></slot>
        </div>

        <div>
          <side-panel-collapse-button/>
        </div>
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
          <a
            v-if="homeButton"
            :href="router.resolve({name: 'main', params: {}}).href"
            class="ffun-page-header-link"
            >Home</a
          >

          <template v-if="globalState.isLoggedIn">
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
                  class="ffun-page-header-link-disabled"
                  v-else
                  >{{ props.text }}</span
                >
              </template>
            </template>
          </template>

          <page-header-external-links :show-api="globalState.isLoggedIn" />
        </div>

        <div class="ffun-page-header-right-block">
          <a
            v-if="globalState.isLoggedIn"
            href="#"
            class="ffun-page-header-link"
            @click.prevent="logout()"
            >logout</a
          >
        </div>
      </div>

      <hr class="my-2 border-slate-400" />

      <main class="mb-4 px-4 min-h-screen">
        <slot></slot>
      </main>

      <footer>
        <slot name="main-footer"></slot>
      </footer>
    </div>
  </div>
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
  const supertokens = useSupertokens();
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

  async function logout() {
    if (settings.authMode === settings.AuthMode.SingleUser) {
      alert("You can't logout in single user mode");
      return;
    }

    await supertokens.logout();

    if (properties.loginRequired) {
      router.push({name: "main", params: {}});
    }
  }

  const hasSideFooter = computed(() => {
    return !!slots["side-footer"];
  });

  function hasSideMenuItem(index: number) {
    return !!slots[`side-menu-item-${index}`];
  }

  watchEffect(() => {
    if (!properties.loginRequired) {
      return;
    }

    if (globalState.isLoggedIn === null) {
      return;
    }

    if (!globalState.isLoggedIn) {
      router.push({name: "main", params: {}});
    }
  });
</script>
