<template>
  <div class="flex my-1">
    <div class="max-w-3xl flex-1 bg-white border rounded p-4">
      <h2
        v-if="url"
        class="mt-0 mb-0"
        ><a
          :href="url"
          target="_blank"
          @click="emit('body-title-clicked')"
          v-html="title" />
      </h2>
      <body-list-references
        v-if="references.length > 0"
        :references="references" />
      <div
        v-if="loading || text"
        class="mt-4">
        <p v-if="loading">loading…</p>
        <div
          v-if="text"
          class="prose max-w-none"
          v-html="text" />
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import _ from "lodash";
  import {computed, ref, useTemplateRef, onMounted} from "vue";
  import type * as t from "@/logic/types";
  import * as events from "@/logic/events";
  import * as e from "@/logic/enums";
  import {computedAsync} from "@vueuse/core";
  import DOMPurify from "dompurify";
  import {useEntriesStore} from "@/stores/entries";

  const entriesStore = useEntriesStore();

  const properties = defineProps<{
    url: string | null;
    title: string | null;
    loading: boolean;
    text: string | null;
    references: t.Reference[];
  }>();

  const emit = defineEmits(["body-title-clicked"]);
</script>
