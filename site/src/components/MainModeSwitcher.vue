<template>

<a href="#" @click="switchMainMode()">{{text}}</a>

</template>

<script lang="ts" setup>
import { computed } from "vue";
import { useRouter } from 'vue-router'
import { useGlobalSettingsStore } from "@/stores/globalSettings";
import * as e from "@/logic/enums";

const globalSettings = useGlobalSettingsStore();

const text = computed(() => {
    return e.MainPanelModeTexts[globalSettings.mainPanelMode];
});

const router = useRouter();

function switchMainMode() {
    if (globalSettings.mainPanelMode === e.MainPanelMode.Feeds) {
        globalSettings.mainPanelMode = e.MainPanelMode.Entries;
    }
    else if (globalSettings.mainPanelMode === e.MainPanelMode.Entries) {
        globalSettings.mainPanelMode = e.MainPanelMode.Feeds;
    }
    else {
        throw new Error("Unknown MainPanelMode");
    }

    router.push({ name: globalSettings.mainPanelMode, params: {} });
}

</script>

<style></style>
