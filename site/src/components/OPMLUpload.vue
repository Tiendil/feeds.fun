<template>
  <div>
    <form
      class="ui-form-row"
      @submit.prevent="submit">
      <ui-file-input
        class="ui-form-row-control"
        :disabled="uploadAction.loading"
        @change="uploadFile" />

      <ui-button
        variant="primary"
        type="submit"
        :disabled="uploadAction.loading"
        @click.prevent="submit"
        >Submit</ui-button
      >
    </form>

    <ui-async-action-status
      :status="uploadAction.status"
      running-text="Loading..."
      succeeded-text="Feeds added!"
      :failed-text="errorMessage" />
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as api from "@/logic/api";
  import {computedAsync} from "@vueuse/core";
  import {useAsyncAction} from "@/logic/asyncAction";
  import {useEntriesStore} from "@/stores/entries";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

  const globalSettings = useGlobalSettingsStore();

  const opmlFile = ref<File | null>(null);

  const uploadAction = useAsyncAction();
  const errorMessage = ref("");

  function uploadFile(event: Event) {
    opmlFile.value = (event.target as HTMLInputElement).files?.[0] ?? null;
    uploadAction.reset();
  }

  async function submit() {
    const file = opmlFile.value;

    if (file === null) {
      return;
    }

    try {
      await uploadAction.run(async () => {
        const reader = new FileReader();

        reader.readAsText(file);
        const content = await new Promise<string>((resolve) => {
          reader.onload = () => {
            resolve(reader.result as string);
          };
        });

        const result = await api.addOPML({content});

        result.match(
          // loading an OPML file is pretty rare and significantly changes the list of feeds
          // => we can force data to be reloaded
          () => {
            globalSettings.updateDataVersion();
          },
          (apiError) => {
            throw apiError;
          }
        );
      });
    } catch (caughtError) {
      if (caughtError instanceof t.ApiError) {
        errorMessage.value = caughtError.message;
      } else {
        console.error(caughtError);
        errorMessage.value = "Error occurred! Maybe you chose a wrong file?";
      }
    }
  }
</script>

<style scoped></style>
