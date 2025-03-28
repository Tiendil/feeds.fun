<template>
  <wide-layout>
    <template #header> Feeds Fun </template>

    <div class="ffun-info-good">
      <p v-if="!linkProcessed">Checking login status...</p>

      <supertokens-login v-else />
    </div>
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

  const linkProcessed = ref(false);

  function goToWorkspace() {
    router.push({name: globalSettings.mainPanelMode, params: {}});
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
    }

    if (await supertokens.hasInitialMagicLinkBeenSent()) {
      await supertokens.handleMagicLinkClicked({
        onSignUp: onSignIn,
        onSignIn: onSignIn,
        onSignFailed: onSignFailed
      });
      linkProcessed.value = true;
    } else {
      linkProcessed.value = true;
    }
  });
</script>

<style></style>
