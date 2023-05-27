<template>

<wide-layout>
  <template #header>
    <h1>Feeds Fun</h1>
  </template>

  <div v-if="isLoggedIn">
    <button @click="goToWorkspace()">Go To Feeds</button>
  </div>

  <div v-else>
    <supertokens-login/>
  </div>

</wide-layout>

</template>

<script lang="ts" setup>
import { useRouter } from "vue-router";
import { useGlobalSettingsStore } from "@/stores/globalSettings";
import { useSupertokens } from "@/stores/supertokens";
import { computedAsync } from "@vueuse/core";

const globalSettings = useGlobalSettingsStore();

const supertokens = useSupertokens();

const router = useRouter();

const isLoggedIn = computedAsync(async () => {
    return await supertokens.isLoggedIn();
});

function goToWorkspace() {
    router.push({ name: globalSettings.mainPanelMode, params: {} });
}

</script>

<style></style>
