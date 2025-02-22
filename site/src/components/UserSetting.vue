<template>
  <div
    v-if="setting !== null"
    class="mb-4">
    <span class="mr-1">{{ setting.name }}</span>

    <input
      class="ffun-input"
      v-if="editing"
      type="input"
      v-model="value" />

    <input
      v-else-if="setting.type !== 'boolean'"
      class="ffun-input"
      disabled
      :value="verboseValue" />

    <config-flag
      v-if="setting.type == 'boolean'"
      style="min-width: 2.5rem"
      :flag="setting.value"
      @update:flag="updateFlag($event)"
      on-text="No"
      off-text="Yes" />

    <template v-else-if="!editing">
      <button
        class="ffun-form-button short ml-1"
        @click.prevent="startEditing()"
        >Edit</button
      >
    </template>

    <template v-else>
      <button
        @click.prevent="save()"
        class="ffun-form-button ml-1"
        >Save</button
      >
      <button
        @click.prevent="cancel()"
        class="ffun-form-button ml-1"
        >Cancel</button
      >
    </template>

    <div
      class="ffun-info-settings"
      v-if="showDescription && setting.description"
      v-html="setting.description" />
  </div>
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
                               showDescription?: boolean}>();

  const value = ref<string | boolean | number | null>(null);

  const editing = ref(false);

  const setting = computed(() => {
    if (properties.kind === null) {
      return null;
    }

    if (globalSettings.userSettings === null) {
      return null;
    }

    return globalSettings.userSettings[properties.kind];
  });

  const verboseValue = computed(() => {
    if (setting.value === null) {
      return "no value";
    }

    const v = setting.value.value;
    const type = setting.value.type;

    if (type == "boolean") {
      return v ? "Yes" : "No";
    }

    if (v == null || v == "") {
      return "no value";
    }

    if (type == "secret") {
      return "********";
    }

    return v;
  });

  async function save() {
    if (value.value === null) {
      return;
    }

    await api.setUserSetting({kind: properties.kind, value: value.value});
    globalSettings.updateDataVersion();
    editing.value = false;
  }

  function cancel() {
    value.value = setting.value && setting.value.value;
    editing.value = false;
  }

  function startEditing() {
    value.value = setting.value && setting.value.value;
    editing.value = true;
  }

  async function updateFlag(newValue: any) {
    value.value = newValue;
    await save();
  }
</script>

<style></style>
