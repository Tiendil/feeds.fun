<template>
<div class="container">
  <div class="nav-panel">
    <h2>Feeds For Fun</h2>

    <ul class="config-menu">
      <li class="config-menu-item">
        I am looking for <main-mode-switcher/>
      </li>

      <li class="config-menu-item">
        For the last
        <config-selector :values="e.LastEntriesPeriodProperties"
                         v-model:property="globalSettings.lastEntriesPeriod"/>
      </li>

      <li class="config-menu-item">
        Sorted by
        <config-selector :values="e.EntriesOrderProperties"
                         v-model:property="globalSettings.entriesOrder"/>
      </li>

      <li class="config-menu-item">
        show already read
      </li>
    </ul>

  </div>

  <div class="main-content">
    <h2>{{mainModeTitle()}}</h2>
    <router-view />
  </div>
</div>
</template>


<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { useGlobalSettingsStore } from "@/stores/globalSettings";
import * as e from "@/logic/enums";

const globalSettings = useGlobalSettingsStore();

function mainModeTitle() {
    if (globalSettings.mainPanelMode === e.MainPanelMode.Feeds) {
        return "Feeds";
    }
    else if (globalSettings.mainPanelMode === e.MainPanelMode.Entries) {
        return "News";
    }
    else {
        throw new Error("Unknown MainPanelMode");
    }
}

</script>

<style scoped>

.container {
    display: flex;
    height: 100vh;
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

  .config-menu-item {
      margin-bottom: 1rem;
  }

</style>
