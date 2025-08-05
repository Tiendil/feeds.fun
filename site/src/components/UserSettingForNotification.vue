<template>
  <a
    v-if="setting"
    href=""
    @click.prevent="updateFlag(true)"
    class=""
    >{{ text }}</a
  >
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch} from "vue";
  import {computedAsync} from "@vueuse/core";
  import * as api from "@/logic/api";
  import * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import {useGlobalSettingsStore} from "@/stores/globalSettings";

  const globalSettings = useGlobalSettingsStore();

  const properties = defineProps<{kind: string; buttonText: string}>();

  const value = ref<boolean | null>(null);

  const setting = computed(() => {
    if (properties.kind === null) {
      return null;
    }

    if (!globalSettings.userSettingsPresent) {
      return null;
    }

    return (globalSettings as any)[properties.kind];
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

  function save() {
    if (value.value === null) {
      return;
    }

    globalSettings.setUserSettings(properties.kind, value.value);
  }

  async function updateFlag(newValue: any) {
    value.value = newValue;
    await save();
  }
</script>

<style></style>
