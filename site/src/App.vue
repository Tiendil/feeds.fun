<template>
<div class="container">
  <div class="nav-panel">
    <h2>Feeds For Fun</h2>

    <ul class="config-menu">
      <li class="config-menu-item">
        Looking for
        <config-selector :values="e.MainPanelModeProperties"
                         v-model:property="globalSettings.mainPanelMode"/>
      </li>

      <template v-if="globalSettings.mainPanelMode == e.MainPanelMode.Entries">

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
          Show tags: <config-flag v-model:flag="globalSettings.showEntriesTags"
                                  on-text="yes"
                                  off-text="no"/>
        </li>

        <li class="config-menu-item">
        Show already read: <config-flag v-model:flag="globalSettings.showRead"
                                        on-text="yes"
                                        off-text="no"/>
        </li>

      </template>

      <template v-if="globalSettings.mainPanelMode == e.MainPanelMode.Feeds">
      </template>

      <template v-if="globalSettings.mainPanelMode == e.MainPanelMode.Rules">
      </template>
    </ul>

    <hr/>

    <a href="#" @click="globalSettings.dataVersion += 1">Reload</a>

    <hr/>

    <tags-filter v-if="globalSettings.mainPanelMode == e.MainPanelMode.Entries"
                 :tags="entriesStore.reportTagsCount"/>

  </div>

  <div class="main-content">
    <router-view />
  </div>
</div>
</template>


<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { useGlobalSettingsStore } from "@/stores/globalSettings";
import { useEntriesStore } from "@/stores/entries";
import * as e from "@/logic/enums";

const globalSettings = useGlobalSettingsStore();
const entriesStore = useEntriesStore();

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

  .config-menu-item {
      margin-bottom: 1rem;
  }

</style>
