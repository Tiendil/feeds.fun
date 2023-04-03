<template>loading...</template>

<script lang="ts" setup>
import { useRouter } from "vue-router";

const router = useRouter();

router.push({ name: "feeds", params: {} });
</script>

<style></style>
