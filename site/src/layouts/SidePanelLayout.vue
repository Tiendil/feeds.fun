<template>
  <div class="flex divide-x ">
    <div class="p-4 w-60 bg-slate-200 flex-shrink-0">
      <h2 class="leading-8 my-0">
        <slot name="main-header"></slot>
      </h2>

      <hr/>

      <ul class="space-y-4">
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
        @click="globalSettings.dataVersion += 1"
        >Reload</a>

      <hr v-if="hasSideFooter" />

      <slot name="side-footer"></slot>
    </div>

    <div class="flex-grow p-4">
      <header class="flex items-center leading-8">
        <div class="display:flex items-center mr-auto">
          <ul class="list-none m-0 p-0 flex space-x-2">
            <li>
              <a
                href="/"
                class="ffun-header-link"
                @click.prevent="router.push({name: 'main', params: {}})"
                >Home</a>
            </li>

            <li
              v-for="[mode, props] of e.MainPanelModeProperties"
              :key="mode">
              <a
                v-if="globalSettings.mainPanelMode !== mode"
                :href="mode"
                class="ffun-header-link"
                @click.prevent="router.push({name: mode, params: {}})">
                {{ props.text }}
              </a>

              <span class="ffun-header-link-disabled cursor-default" v-else>{{ props.text }}</span>
            </li>

            <li>
              <a
                href="/api/docs"
                target="_blank"
                class="ffun-header-link"
                style="text-decoration: none"
                >API&#8599;</a
              >
            </li>

            <li>
              <a
                :href="settings.githubRepo"
                target="_blank"
                class="ffun-header-link"
                style="text-decoration: none"
                >GitHub&#8599;</a
              >
            </li>
          </ul>
        </div>

        <div class="flex items-center ml-4">
          <a href="#"
             class="ffun-header-link"
             @click.prevent="logout()"
             >logout</a>
        </div>
      </header>

      <hr class="my-2 border-slate-400" />

      <div
        v-if="showApiKeyMessage"
        class="ffun-info-normal">
        <p>
          Because, for now, our service is free to use and OpenAI API costs money, we politely ask you to set up your
          own OpenAI API key.
        </p>
        <p>
          You can do this on the
          <a
            href="#"
            @click.prevent="router.push({name: e.MainPanelMode.Settings, params: {}})"
            >settings</a
          >
          page.
        </p>
        <user-setting kind="openai_hide_message_about_setting_up_key" />
      </div>

      <main class="mb-4">
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
  import {useEntriesStore} from "@/stores/entries";
  import {useSupertokens} from "@/stores/supertokens";
  import * as e from "@/logic/enums";
  import * as settings from "@/logic/settings";

  const globalSettings = useGlobalSettingsStore();
  const entriesStore = useEntriesStore();
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

  const showApiKeyMessage = computed(() => {
    return (
      globalSettings.userSettings &&
      !globalSettings.userSettings.openai_api_key.value &&
      !globalSettings.userSettings.openai_hide_message_about_setting_up_key.value
    );
  });

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
