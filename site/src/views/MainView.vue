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

    <h2>Web-based news reader</h2>

    <ul class="main-page-element">
      <li>Reader automatically assigns tags to news entries.</li>
      <li>You create rules to score news by tags.</li>
      <li>Filter and sort news how you want, to read only what you want.</li>
      <li>?????</li>
      <li>Profit.</li>
    </ul>

    <h2>You are in control</h2>

    <ul class="main-page-element">
      <li>No black box recommendation algorithms.</li>
      <li>No "smart" reordering of your news.</li>
      <li>No ads.</li>
      <li>No selling of your data.</li>
    </ul>

    <h2>How it looks like</h2>

    <img
      src="/news-filtering-example.png"
      alt="News filtering example" />

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

<style>
  .main-page-element {
      @apply list-disc list-inside text-left max-w-md mx-auto;
  }
</style>
