<template>
  <div class="flex-shrink-0 w-8 text-right pr-1">
    <favicon-element
      :url="url"
      class="w-5 h-5 mx-1 inline align-text-bottom" />
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
    url: string;
  }>();
</script>
