<template>
  <router-view />
</template>

<script setup lang="ts">
  import {onMounted} from "vue";
import { watchEffect } from "vue";
import {useRoute, useRouter} from "vue-router";
import * as marketing from "@/logic/marketing";

let route = useRoute();
let router = useRouter();

watchEffect(() => {
  marketing.processUTM(route, router);
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
