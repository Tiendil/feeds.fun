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

      <slot name="side-menu"></slot>

    </ul>

    <hr v-if="reload"/>

    <a v-if="reload"
       href="#"
       @click="globalSettings.dataVersion += 1">Reload</a>

    <hr v-if="hasSideFooter"/>

    <slot name="side-footer"></slot>
  </div>

  <div class="main-content">
    <header>
      <slot name="main-header"></slot>
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
import { ref, computed, useSlots } from 'vue';
import { useRouter, RouterLink, RouterView } from 'vue-router'
import { useGlobalSettingsStore } from "@/stores/globalSettings";
import { useEntriesStore } from "@/stores/entries";
import { useSupertokens } from "@/stores/supertokens";
import * as e from "@/logic/enums";

const globalSettings = useGlobalSettingsStore();
const entriesStore = useEntriesStore();
const supertokens = useSupertokens();

const router = useRouter();
const slots = useSlots()


const properties = withDefaults(defineProps<{reload: bool}>(),
                                {reload: true});

async function logout() {
    await supertokens.logout();
    router.push({ name: 'main', params: {} });
}

const hasSideFooter = computed(() => {
    return !!slots['side-footer'];
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
