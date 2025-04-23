<template>
  <router-view />
</template>

<script setup lang="ts">
  import {onMounted} from "vue";
  import {watchEffect} from "vue";
import {useRoute, useRouter} from "vue-router";
import { StorageSerializers, useStorage } from '@vueuse/core'
  import {useGlobalState} from "@/stores/globalState";
import * as marketing from "@/logic/marketing";
  import * as events from "@/logic/events";

  const route = useRoute();
  const router = useRouter();
const utmStorage = useStorage('ffun_utm', null, undefined, { serializer: StorageSerializers.object });
  const globalState = useGlobalState();

  watchEffect(() => {
    marketing.processUTM(route, router, utmStorage);
  });

  watchEffect(async () => {
    if (utmStorage.value && globalState.isLoggedIn && Object.keys(utmStorage.value).length > 0) {
      await events.trackUtm(utmStorage.value);
      utmStorage.value = null;
    }
  });
</script>

<style scoped>
  .container {
    display: flex;
  }

  .nav-panel {
    width: 10rem;
    flex-shrink: 0;
    background-color: #f0f0f0;
    padding: 1rem;
  }

  .main-content {
    flex-grow: 1;
    padding: 1rem;
  }

  .config-menu {
    list-style-type: none;
    margin: 0;
    padding: 0;
  }

  .config-menu-item {
    margin-bottom: 1rem;
  }
</style>
