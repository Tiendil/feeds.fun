<template>
  <div class="flex flex-col items-stretch rounded-xl overflow-hidden min-h-28 max-h-28 mx-2">
    <div class="bg-blue-100 py-1 items-center text-xl font-medium">
      <slot name="caption" />
    </div>

    <div class="flex-1 bg-slate-100 p-2 text-gray-800 flex items-center">
      <div class="">
        <slot name="description" />
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import * as t from "@/logic/types";
  import {computed, ref, inject} from "vue";
  import type {Ref} from "vue";
  import {useTagsStore} from "@/stores/tags";
  import * as tagsFilterState from "@/logic/tagsFilterState";
  import * as asserts from "@/logic/asserts";
  import * as events from "@/logic/events";

  const properties = defineProps<{
    icon: string;
  }>();
</script>
