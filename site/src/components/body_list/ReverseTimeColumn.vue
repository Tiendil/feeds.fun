<template>
<div class="flex-shrink-0 w-16 cursor-default text-right"
     :title="title">
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

  const topElement = useTemplateRef("entryTop");

  const properties = defineProps<{
    time: Date|null;
    title: string;
  }>();

</script>
