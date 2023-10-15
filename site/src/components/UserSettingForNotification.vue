<template>
  <button v-if="setting"
          @click.prevent="updateFlag(true)"
          class="ffun-form-button">{{ text }}</button>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch} from "vue";
  import {computedAsync} from "@vueuse/core";
  import * as api from "@/logic/api";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

  const globalSettings = useGlobalSettingsStore();

const properties = defineProps<{kind: string,
                                buttonText: string}>();

  const value = ref<boolean | null>(null);

  const setting = computed(() => {
    if (properties.kind === null) {
      return null;
    }

    if (globalSettings.userSettings === null) {
      return null;
    }

    return globalSettings.userSettings[properties.kind];
  });

const text = computed(() => {
  if (properties.buttonText) {
    return properties.buttonText;
  }

  if (setting.value === null) {
    return "";
  }

  return setting.value.name;
});

  async function save() {
    if (value.value === null) {
      return;
    }

    await api.setUserSetting({kind: properties.kind, value: value.value});
    globalSettings.updateDataVersion();
  }

async function updateFlag(newValue: any) {
  value.value = newValue;
  await save();
}

</script>

<style></style>
