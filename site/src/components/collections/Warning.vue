<template>
  <div class="ffun-info-attention">
    <h3>
      Remember about <a
                       class="ffun-normal-link"
        href="#"
        @click.prevent="goToCollections()"
        >collections</a
      ></h3>
    <p
      >!</p
    >
    <p>!</p>
  </div>
</template>

<script lang="ts" setup>
  import {useRouter} from "vue-router";
import * as e from "@/logic/enums";

  const router = useRouter();

  function goToCollections() {
    router.push({name: e.MainPanelMode.Collections, params: {}});
  }
</script>
