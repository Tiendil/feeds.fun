<template>

<a href="#" @click="switchMainMode()">{{globalSettings.mainPanelMode}}</a>

</template>

<script lang="ts" setup>

import { useRouter } from 'vue-router'
import { useGlobalSettingsStore } from "@/stores/globalSettings";
import * as e from "@/logic/enums";

const globalSettings = useGlobalSettingsStore();

const router = useRouter();

function switchMainMode() {
    if (globalSettings.mainPanelMode === e.MainPanelMode.Feeds) {
        globalSettings.mainPanelMode = e.MainPanelMode.News;
    }
    else if (globalSettings.mainPanelMode === e.MainPanelMode.News) {
        globalSettings.mainPanelMode = e.MainPanelMode.Feeds;
    }
    else {
        throw new Error("Unknown MainPanelMode");
    }

    router.push({ name: globalSettings.mainPanelMode, params: {} });
}

</script>

<style></style>
