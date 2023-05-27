<template>
    <div v-if="isLoggedIn">
      <button @click="goToWorkspace()">Go To Feeds</button>
    </div>

    <div v-else>
      <supertokens-login/>
    </div>
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

if (await supertokens.isLoggedIn()) {
    goToWorkspace();
}

else {

    async function onSignIn() {
        goToWorkspace();
    }

    async function onSignFailed() {
        await supertokens.clearLoginAttempt();
    }

    if (supertokens.hasInitialMagicLinkBeenSent()) {
        supertokens.handleMagicLinkClicked({onSignUp: onSignIn,
                                            onSignIn: onSignIn,
                                            onSignFailed: onSignFailed});
    }
    else {
    }
}


</script>

<style></style>
