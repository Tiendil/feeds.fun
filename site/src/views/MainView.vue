<template>

<wide-layout>
  <template #header>
    Feeds Fun
  </template>

  <div v-if="globalState.isLoggedIn">
    <p>You have already logged in.</p>
    <button @click="goToWorkspace()">Go To Feeds</button>
  </div>

  <div v-else>
    <supertokens-login/>
  </div>

  <br/>
  <github-button :href="settings.githubRepo + '/subscription'">Watch</github-button>
  &nbsp;
  <github-button :href="settings.githubRepo" data-show-count="true">Star</github-button>
  &nbsp;
  <github-button :href="settings.githubRepo + '/issues'" data-show-count="true">Issue</github-button>
  &nbsp;
  <github-button :href="settings.githubRepo + '/discussions'" data-show-count="true">Discuss</github-button>

  <h2>What is it?</h2>

  <ul style="text-align: left;">
    <li>Web-based RSS reader.</li>
    <li>For each news entry automatically adds tags. With the help of AI, of course.</li>
    <li>You create rules to score articles by tags.</li>
    <li>You filter recent articles by tags and sort by score.</li>
    <li>
      You are in control of what you read:
      <ul>
        <li>no black box recommendations algorithms</li>
        <li>no "smart" reordering of your news</li>
        <li>no advertisements</li>
        <li>no selling of your data</li>
      </ul>
    </li>
  </ul>

  <h2>What will it become?</h2>

  <ul style="text-align: left;">
    <li>Will become much prettier.</li>
    <li>
      Will collecting not only RSS but any news feeds:
      <ul>
        <li>news from social networks</li>
        <li>GitHub stars activity</li>
        <li>Steam games releases</li>
        <li>new scientific papers</li>
        <li>etc.</li>
      </ul>
    </li>
    <li>Will be open-sourced.</li>
    <li>Will be self-hosted. If you don&apos;t want to use centralized service.</li>
  </ul>

</wide-layout>

</template>

<script lang="ts" setup>
import { useRouter } from "vue-router";
import { useGlobalSettingsStore } from "@/stores/globalSettings";
import { useSupertokens } from "@/stores/supertokens";
import { useGlobalState } from "@/stores/globalState";
import { computedAsync } from "@vueuse/core";
import * as settings from "@/logic/settings";

const globalSettings = useGlobalSettingsStore();
const globalState = useGlobalState();

const supertokens = useSupertokens();

const router = useRouter();

function goToWorkspace() {
    router.push({ name: globalSettings.mainPanelMode, params: {} });
}

</script>

<style></style>
