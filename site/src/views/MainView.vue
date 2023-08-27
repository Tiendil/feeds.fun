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

    <p>
      <i>Web-based news reader. Self-hosted, if it is your way.</i>
    </p>

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

    <h2>Screenshots</h2>

    <p><i>GUI is still in the early development stage, like the whole project. It will become more pleasurable.</i></p>

    <img
      src="/news-filtering-example.png"
      alt="News filtering example" />

    <p class="main-page-element"><strong>Explanation</strong></p>

    <ul class="main-page-element">
      <li>From the news for the last week, sorted by score.</li>
      <li>Show only news about <code>game-development</code> from <code>reddit.com</code>.</li>
      <li>Exclude news related to <code>employment</code>.</li>
      <li>Hide already read news.</li>
    </ul>

    <p class="main-page-element"><strong>Tags sorting for news records</strong></p>

    <ul class="main-page-element">
      <li>Tags are sorted by the impact on the score.</li>
      <li>Green tags have a positive impact.</li>
      <li>Red tags have a negative impact.</li>
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

<style>
  .main-page-element {
    text-align: left;
    margin-left: auto;
    max-width: 27rem;
    margin-right: auto;
  }
</style>
