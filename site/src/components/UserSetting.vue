<template>
  <div style="margin-bottom: 1rem">
    <label>
      <strong>{{ setting.name }}:</strong>
      &nbsp;
      <input
        v-if="editing"
        type="input"
        v-model="value" />
      <span v-else>{{ verboseValue }}</span>
    </label>

    &nbsp;

    <template v-if="setting.type == 'boolean'">
      <button
        v-if="!setting.value"
        @click.prevent="turnOn()"
        >Turn on</button
      >

      <button
        v-if="setting.value"
        @click.prevent="turnOff()"
        >Turn off</button
      >
    </template>

    <template v-else-if="!editing">
      <button @click.prevent="startEditing()">Edit</button>
    </template>

    <template v-else>
      <button @click.prevent="save()">Save</button>
      &nbsp;
      <button @click.prevent="cancel()">Cancel</button>
    </template>

    <div
      v-if="setting.description"
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

  const properties = defineProps<{kind: string}>();

  const value = ref<string | null>(null);

  const editing = ref(false);

  const setting = computed(() => {
    if (properties.kind === null) {
      return null;
    }

    return globalSettings.userSettings[properties.kind];
  });

  const verboseValue = computed(() => {
    const v = setting.value.value;
    const type = setting.value.type;

    if (type == "boolean") {
      return v ? "Yes" : "No";
    }

    if (v == null || v == "") {
      return "—";
    }

    if (type == "secret") {
      return "********";
    }

    return v;
  });

  async function save() {
    await api.setUserSetting({kind: properties.kind, value: value.value});
    globalSettings.updateDataVersion();
    editing.value = false;
  }

  function cancel() {
    value.value = setting.value.value;
    editing.value = false;
  }

  function startEditing() {
    value.value = setting.value.value;
    editing.value = true;
  }

  async function turnOn() {
    value.value = true;
    await save();
  }

  async function turnOff() {
    value.value = false;
    await save();
  }
</script>

<style></style>
