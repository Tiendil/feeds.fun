<template>
  <div>
    <input
      type="file"
      @change="uploadFile" />
    <button
      type="submit"
      @click.prevent="submit"
      >Submit</button
    >
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import {useEntriesStore} from "@/stores/entries";

  const opmlFile = ref<File | null>(null);

  function uploadFile(event: Event) {
    opmlFile.value = (event.target as HTMLInputElement).files?.[0] ?? null;
  }

  async function submit() {
    if (opmlFile.value === null) {
      return;
    }

    const reader = new FileReader();

    reader.readAsText(opmlFile.value);
    const content = await new Promise<string>((resolve) => {
      reader.onload = () => {
        resolve(reader.result as string);
      };
    });

    await api.addOPML({content: content});
  }
</script>

<style scoped></style>
