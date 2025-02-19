<template>
  <div class="flex divide-x">
    <div class="p-4 w-60 bg-slate-50 flex-shrink-0">
      <h2 class="leading-8 my-0">
        <slot name="main-header"></slot>
      </h2>

      <hr />

      <ul class="space-y-2">
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
        class="ffun-form-button p-1 my-1 block w-full text-center"
        v-if="reloadButton"
        href="#"
        @click="globalSettings.updateDataVersion()"
        >Refresh</a
      >

      <hr v-if="hasSideFooter" />

      <slot name="side-footer"></slot>
    </div>

    <div class="flex-grow">
      <header class="flex items-center leading-8 px-4 pt-4">
        <div class="display:flex items-center mr-auto">
          <ul class="list-none m-0 p-0 flex space-x-2">
            <li
              v-for="[mode, props] of e.MainPanelModeProperties"
              :key="mode">
              <a
                v-if="globalSettings.mainPanelMode !== mode"
                :href="router.resolve({name: mode, params: {}}).href"
                class="ffun-header-link"
                @click.prevent="router.push({name: mode, params: {}})">
                {{ props.text }}
              </a>

              <span
                class="ffun-header-link-disabled cursor-default"
                v-else
                >{{ props.text }}</span
              >
            </li>

            <li class="">
              <a
                href="/api/docs"
                target="_blank"
                class="ffun-header-link"
                style="text-decoration: none"
                @click="events.socialLinkClicked({linkType: 'api'})"
                >API</a
              >
            </li>

            <li v-if="settings.blog">
              <a
                :href="settings.blog"
                target="_blank"
                class="ffun-header-link"
                style="text-decoration: none"
                @click="events.socialLinkClicked({linkType: 'blog'})"
                >Blog</a
              >
            </li>

            <li v-if="settings.redditSubreddit">
              <a
                :href="settings.redditSubreddit"
                target="_blank"
                class="ffun-header-link text-xl align-middle"
                title="Reddit"
                style="text-decoration: none"
                @click="events.socialLinkClicked({linkType: 'reddit'})"
                ><i class="ti ti-brand-reddit"></i
              ></a>
            </li>

            <li v-if="settings.discordInvite">
              <a
                :href="settings.discordInvite"
                target="_blank"
                class="ffun-header-link text-xl align-middle"
                title="Discord"
                style="text-decoration: none"
                @click="events.socialLinkClicked({linkType: 'discord'})"
                ><i class="ti ti-brand-discord"></i
              ></a>
            </li>

            <li v-if="settings.githubRepo">
              <a
                :href="settings.githubRepo"
                target="_blank"
                class="ffun-header-link text-xl align-middle"
                title="GitHub"
                style="text-decoration: none"
                @click="events.socialLinkClicked({linkType: 'github'})">
                <i class="ti ti-brand-github"></i
              ></a>
            </li>
          </ul>
        </div>

        <div class="flex items-center ml-4">
          <a
            href="#"
            class="ffun-header-link"
            @click.prevent="logout()"
            >logout</a
          >
        </div>
      </header>

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
