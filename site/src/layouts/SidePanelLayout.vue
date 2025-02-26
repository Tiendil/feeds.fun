<template>
  <div class="ffun-side-panel-layout">
    <div class="ffun-side-panel">
      <div class="ffun-page-header">
        <div class="ffun-page-header-title">
          <slot name="main-header"></slot>
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
            <template
              v-for="[mode, props] of e.MainPanelModeProperties"
              :key="mode">
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

              <a
                href="/api/docs"
                target="_blank"
                class="ffun-page-header-link"
                @click="events.socialLinkClicked({linkType: 'api'})"
                >API</a
              >

              <a
                v-if="settings.blog"
                :href="settings.blog"
                target="_blank"
                class="ffun-page-header-link"
                @click="events.socialLinkClicked({linkType: 'blog'})"
                >Blog</a
              >

              <a
                v-if="settings.redditSubreddit"
                :href="settings.redditSubreddit"
                target="_blank"
                class="ffun-page-header-link text-xl align-middle"
                title="Reddit"
                @click="events.socialLinkClicked({linkType: 'reddit'})"
                ><i class="ti ti-brand-reddit"></i
              ></a>

              <a
                v-if="settings.discordInvite"
                :href="settings.discordInvite"
                target="_blank"
                class="ffun-page-header-link text-xl align-middle"
                title="Discord"
                @click="events.socialLinkClicked({linkType: 'discord'})"
                ><i class="ti ti-brand-discord"></i
              ></a>

              <a
                v-if="settings.githubRepo"
                :href="settings.githubRepo"
                target="_blank"
                class="ffun-page-header-link text-xl align-middle"
                title="GitHub"
                @click="events.socialLinkClicked({linkType: 'github'})">
                <i class="ti ti-brand-github"></i
              ></a>
          </div>

          <div class="ffun-page-header-right-block">
              <a
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

  const properties = withDefaults(defineProps<{reloadButton?: boolean; loginRequired?: boolean}>(), {
    reloadButton: true,
    loginRequired: true
  });

  async function logout() {
    if (settings.authMode === settings.AuthMode.SingleUser) {
      alert("You can't logout in single user mode");
      return;
    }

    await supertokens.logout();
    router.push({name: "main", params: {}});
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
