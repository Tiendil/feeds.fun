<template>
  <div class="flex min-h-9 items-center justify-end rounded border border-slate-200 bg-slate-50 px-2 py-1">
    <product-tokens
      v-if="globalState.loginConfirmed && productState !== null"
      :tokens="productState.tokens" />
  </div>
</template>

<script lang="ts" setup>
  import {computedAsync} from "@vueuse/core";

  import * as api from "@/logic/api";
  import {useEntriesStore} from "@/stores/entries";
  import {useGlobalState} from "@/stores/globalState";

  const entriesStore = useEntriesStore();
  const globalState = useGlobalState();

  const productState = computedAsync(async () => {
    entriesStore.entriesLoadRevision;

    if (!globalState.loginConfirmed) {
      return null;
    }

    // TODO: Bind product-state loading to globalSettings.dataVersion instead
    //       if it is displayed outside the News view.
    return await api.getProductState();
  }, null);
</script>
