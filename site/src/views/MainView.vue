<template>
  <wide-layout>
    <template #header> Feeds Fun </template>

    <div class="border-2 border-green-300 bg-green-50 max-w-md mx-auto p-2">
      <div v-if="globalState.isLoggedIn">
        <p>You have already logged in.</p>
        <button class="text-blue-600 hover:text-blue-800 text-xl pt-0"
                @click.prevent="goToWorkspace()">Go To Feeds ⇒</button>
      </div>

      <supertokens-login v-else />
    </div>

    <h2>News reader with tags</h2>

    <ul class="main-page-element">
      <li>Reader automatically assigns tags to news.</li>
      <li>You create rules to score news by tags.</li>
      <li>Filter and sort news how you want  ⇒ read only what you want.</li>
    </ul>

    <h2>You are in control</h2>

    <ul class="main-page-element">
      <li>No black box recommendation algorithms.</li>
      <li>No "smart" reordering.</li>
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
