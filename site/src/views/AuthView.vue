<template>
  <wide-layout>
    <template #header> Feeds Fun </template>

    <div v-if="!linkProcessed">Checking login status...</div>

    <div v-else-if="globalState.isLoggedIn">
      <button @click="goToWorkspace()">Go To Feeds</button>
    </div>

    <div v-else>
      <supertokens-login />
    </div>
  </wide-layout>
</template>

<script lang="ts" setup>
  import {useRouter} from "vue-router";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";
  import {useSupertokens} from "@/stores/supertokens";
  import {useGlobalState} from "@/stores/globalState";
  import {computedAsync} from "@vueuse/core";
  import {computed, ref, onBeforeMount} from "vue";
  import * as settings from "@/logic/settings";

  const globalSettings = useGlobalSettingsStore();
  const globalState = useGlobalState();

  const supertokens = useSupertokens();

  const router = useRouter();

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
