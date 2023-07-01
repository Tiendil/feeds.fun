<template>
<div style="margin-bottom: 1rem;">

    <label>
      <span>{{setting.name}}:</span>
      &nbsp;
      <input v-if="editing" type="input" v-model="value" />
      <span v-else>{{setting.value}}</span>
    </label>

    &nbsp;

    <template v-if="!editing">
      <button @click.prevent="startEditing()">Edit</button>
    </template>

    <template v-else>
      <button @click.prevent="save()">Save</button>
      &nbsp;
      <button @click.prevent="cancel()">Cancel</button>
    </template>

    <p v-if="setting.description">{{setting.description}}</p>

</div>
</template>

<script lang="ts" setup>
import { computed, ref, onUnmounted, watch } from "vue";
import { computedAsync } from "@vueuse/core";
import * as api from "@/logic/api";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";
import { useGlobalSettingsStore } from "@/stores/globalSettings";

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


async function save() {
    await api.setUserSetting({kind: properties.kind,
                              value: value.value});
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

</script>

<style></style>
