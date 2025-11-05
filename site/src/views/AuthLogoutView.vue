<template>
  <wide-layout>
    <div class="max-w-xl mx-auto px-6 py-12 text-center">
      <h1 class="text-3xl font-semibold mb-4">Signing you out…</h1>
      <p class="text-gray-600 mb-6"> We are ending your current session. You will be redirected automatically. </p>
      <p class="text-sm text-gray-500"
        >If nothing happens,
        <a
          :href="logoutUrl"
          class="text-indigo-600"
          >click here</a
        >.</p
      >
    </div>
  </wide-layout>
</template>

<script lang="ts" setup>
  import {computed, onMounted} from "vue";
  import {useRoute} from "vue-router";

  const route = useRoute();

  const logoutUrl = computed(() => {
    const defaultReturn = `${window.location.origin}/?logged-out`;
    const returnTo = typeof route.query.return_to === "string" ? route.query.return_to : defaultReturn;
    const url = new URL(window.location.origin + "/self-service/logout/browser");
    url.searchParams.set("return_to", returnTo);
    return url.toString();
  });

  onMounted(() => {
    window.location.replace(logoutUrl.value);
  });
</script>
