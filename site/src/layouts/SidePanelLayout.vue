<template>
<div class="container">
  <div class="nav-panel">
    <h2 style="margin-top: 0; margin-bottom: 0;">Feeds For Fun</h2>

    <a href="#" @click.prevent="logout()">logout</a>

    <hr/>

    <ul class="config-menu">
      <li class="config-menu-item">
        Looking for
        <config-selector :values="e.MainPanelModeProperties"
                         v-model:property="globalSettings.mainPanelMode"/>
      </li>

      <li v-if="hasSideMenuItem(1)"
          class="config-menu-item">
        <slot name="side-menu-item-1"></slot>
      </li>

      <li v-if="hasSideMenuItem(2)"
          class="config-menu-item">
        <slot name="side-menu-item-2"></slot>
      </li>

      <li v-if="hasSideMenuItem(3)"
          class="config-menu-item">
        <slot name="side-menu-item-3"></slot>
      </li>

      <li v-if="hasSideMenuItem(4)"
          class="config-menu-item">
        <slot name="side-menu-item-4"></slot>
      </li>

      <li v-if="hasSideMenuItem(5)"
          class="config-menu-item">
        <slot name="side-menu-item-5"></slot>
      </li>

    </ul>

    <hr v-if="reloadButton"/>

    <a v-if="reloadButton"
       href="#"
       @click="globalSettings.dataVersion += 1">Reload</a>

    <hr v-if="hasSideFooter"/>

    <slot name="side-footer"></slot>
  </div>

  <div class="main-content">
    <header>
      <h2 style="margin-top: 0;">
        <slot name="main-header"></slot>
      </h2>
    </header>

    <main>
      <slot></slot>
    </main>

    <footer>
      <slot name="main-footer"></slot>
    </footer>
  </div>
</div>
</template>

<script lang="ts" setup>
    import { ref, computed, useSlots, onMounted, watch, watchEffect } from 'vue';
import { useRouter, RouterLink, RouterView } from 'vue-router'
import { useGlobalSettingsStore } from "@/stores/globalSettings";
import { useGlobalState } from "@/stores/globalState";
import { useEntriesStore } from "@/stores/entries";
import { useSupertokens } from "@/stores/supertokens";
import * as e from "@/logic/enums";
import * as settings from "@/logic/settings";

const globalSettings = useGlobalSettingsStore();
const entriesStore = useEntriesStore();
const supertokens = useSupertokens();
const globalState = useGlobalState();

const router = useRouter();
const slots = useSlots()


const properties = withDefaults(defineProps<{reloadButton?: bool,
                                             loginRequired?: bool}>(),
                                {reloadButton: true,
                                 loginRequired: true});

async function logout() {
    if (settings.authMode === settings.AuthMode.SingleUser) {
        alert("You can't logout in single user mode");
        return;
    }

    await supertokens.logout();
    router.push({ name: 'main', params: {} });
}

const hasSideFooter = computed(() => {
    return !!slots['side-footer'];
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
        router.push({ name: 'main', params: {} });
    }
});

</script>

<style scoped>

  .container {
    display: flex;
  }

  .nav-panel {
    width: 10rem;
    flex-shrink: 0;
    background-color: #f0f0f0;
    padding: 1rem;
  }

  .main-content {
    flex-grow: 1;
    padding: 1rem;
  }

  .config-menu {
      list-style-type: none;
      margin: 0;
      padding: 0;
  }

  :deep(.config-menu-item) {
      margin-bottom: 1rem;
  }

</style>
