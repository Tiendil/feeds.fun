<template>
  <ui-button
    variant="secondary"
    size="compact"
    @click="goToAddFeed()">
    Add feed
  </ui-button>
</template>

<script lang="ts" setup>
  import {useRouter} from "vue-router";
  import * as e from "@/logic/enums";
  import * as navigation from "@/logic/navigation";

  const router = useRouter();

  function goToAddFeed() {
    router.push({
      name: e.MainPanelMode.Discovery,
      hash: `#${navigation.discoverySectionIds.addFeed}`
    });
  }
</script>
