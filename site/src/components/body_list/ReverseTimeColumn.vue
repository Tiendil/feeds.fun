<template>
  <div
    class="w-16 flex-shrink-0 cursor-help rounded-sm text-right focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
    tabindex="0">
    <value-date-time
      class=""
      :value="time"
      :reversed="true" />
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
    time: Date | null;
  }>();
</script>
