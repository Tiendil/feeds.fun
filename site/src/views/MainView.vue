<template>loading...</template>

<script lang="ts" setup>
import { useRouter } from "vue-router";
import { useGlobalSettingsStore } from "@/stores/globalSettings";

const globalSettings = useGlobalSettingsStore();

const router = useRouter();

router.push({ name: globalSettings.mainPanelMode, params: {} });

</script>

<style></style>
