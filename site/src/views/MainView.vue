<template>
  <wide-layout>
    <template #header> Feeds Fun </template>

    <div v-if="globalState.isLoggedIn">
      <p>You have already logged in.</p>
      <button @click.prevent="goToWorkspace()">Go To Feeds</button>
    </div>

    <div v-else>
      <supertokens-login />
    </div>

    <br />

    <ffun-github-buttons :repository="settings.githubRepo" />

    <h2>What is it?</h2>

    <ul style="text-align: left">
      <li>Web-based news reader. Self-hosted, if it is your way.</li>
      <li>Automatically assigns tags to news entries.</li>
      <li>You create rules to score news by tags.</li>
      <li>Then filter and sort news how you want.</li>
    </ul>

    <h2>You are in control</h2>

    <ul style="text-align: left">
      <li>No black box recommendation algorithms.</li>
      <li>No "smart" reordering of your news.</li>
      <li>No ads.</li>
      <li>No selling of your data.</li>
    </ul>

    <h2>What will it become?</h2>

    <ul style="text-align: left">
      <li>Will become much prettier.</li>
      <li> Will collect not only RSS/ATOM but any news feeds, including private if you allow. </li>
      <li>Will suggest new rules to score & new feeds, if you allow.</li>
    </ul>
  </wide-layout>
</template>

<script lang="ts" setup>
  import {useRouter} from "vue-router";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useSupertokens} from "@/stores/supertokens";
  import {useGlobalState} from "@/stores/globalState";
  import {computedAsync} from "@vueuse/core";
  import * as settings from "@/logic/settings";
  import * as e from "@/logic/enums";

  const globalSettings = useGlobalSettingsStore();
  const globalState = useGlobalState();

  const supertokens = useSupertokens();

  const router = useRouter();

  function goToWorkspace() {
    router.push({name: e.MainPanelMode.Entries, params: {}});
  }
</script>

<style></style>
