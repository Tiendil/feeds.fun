<template>
  <wide-layout>
    <div class="ffun-page-header">
      <div class="ffun-page-header-center-block">
        <page-header-external-links :show-api="false" />
      </div>
    </div>

    <hr />

    <main-block>
      <h1 class="m-0 text-5xl">Feeds Fun</h1>
      <p class="mt-2 text-2xl">Transparent Personalized News</p>
    </main-block>

    <main-block>
      <div class="max-w-xl md:mx-auto ffun-info-good text-center mx-2">
        <p>Checking login status...</p>
      </div>
    </main-block>
  </wide-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch, provide, onBeforeMount} from "vue";
  import {useRouter} from "vue-router";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useSupertokens} from "@/stores/supertokens";
  import {useGlobalState} from "@/stores/globalState";
  import {computedAsync} from "@vueuse/core";
  import * as settings from "@/logic/settings";

  const globalSettings = useGlobalSettingsStore();
  const globalState = useGlobalState();

  const supertokens = useSupertokens();

  const router = useRouter();

  provide("eventsViewName", "auth");

  function goToWorkspace() {
    router.push({name: globalSettings.mainPanelMode, params: {}});
  }

  function goToMain() {
    router.push({name: "main", params: {}});
  }

  onBeforeMount(async () => {
    if (globalState.isLoggedIn) {
      goToWorkspace();
      return;
    }

    async function onSignIn() {
      goToWorkspace();
    }

    async function onSignFailed() {
      await supertokens.clearLoginAttempt();
      goToMain();
    }

    if (await supertokens.hasInitialMagicLinkBeenSent()) {
      await supertokens.handleMagicLinkClicked({
        onSignUp: onSignIn,
        onSignIn: onSignIn,
        onSignFailed: onSignFailed
      });
    } else {
      goToMain();
    }
  });
</script>

<style></style>
