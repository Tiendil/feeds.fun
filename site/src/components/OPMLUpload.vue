<template>
  <div>
    <form @submit.prevent="submit">
      <input
        type="file"
        class="ffun-file-button"
        :disabled="loading"
        @change="uploadFile" />

      <button
        class="ffun-form-button"
        type="submit"
        :disabled="loading"
        @click.prevent="submit"
        >Submit</button
      >
    </form>

    <p
      v-if="loading"
      class="ffun-info-waiting mt-2"
      >Loading...</p
    >

    <p
      v-if="loaded"
      class="ffun-info-good mt-4"
      >Feeds added!</p
    >

    <p
      v-if="error"
      class="ffun-info-bad mt-4">
      {{ errorMessage }}
    </p>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import {useEntriesStore} from "@/stores/entries";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

  const globalSettings = useGlobalSettingsStore();

  const opmlFile = ref<File | null>(null);

  const loading = ref(false);
  const loaded = ref(false);
  const error = ref(false);
  const errorMessage = ref("");

  function uploadFile(event: Event) {
    opmlFile.value = (event.target as HTMLInputElement).files?.[0] ?? null;
    loaded.value = false;
  }

  async function submit() {
    if (opmlFile.value === null) {
      return;
    }

    loading.value = true;
    loaded.value = false;
    error.value = false;

    const reader = new FileReader();

    reader.readAsText(opmlFile.value);
    const content = await new Promise<string>((resolve) => {
      reader.onload = () => {
        resolve(reader.result as string);
      };
    });

    try {
      let result = await api.addOPML({content: content});

      result.match(
        // loading an OPML file is pretty rare and significantly changes the list of feeds
        // => we can force data to be reloaded
        (data) => {
          globalSettings.updateDataVersion();
          error.value = false;
          loaded.value = true;
        },
        (err) => {
          error.value = true;
          errorMessage.value = err.message;
          loaded.value = false;
        }
      );

      loading.value = false;
    } catch (e) {
      console.error(e);
      loading.value = false;
      loaded.value = false;
      error.value = true;
      error.message = "Error occurred! Maybe you chose a wrong file?";
    }
  }
</script>

<style scoped></style>
