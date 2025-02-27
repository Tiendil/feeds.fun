<template>

  <!-- PC -->
  <div class="hidden md:flex items-stretch rounded-xl overflow-hidden min-h-28 max-h-28 mx-2">
    <div class="w-12 bg-blue-200 flex items-center justify-center text-4xl font-bold">
      <i :class="['ti', icon]"></i>
    </div>

    <div class="w-1/3 bg-blue-100 px-4 flex items-center text-xl font-medium">
      <slot name="caption" />
    </div>

    <div class="flex-1 bg-slate-100 p-6 text-gray-800 flex items-center">
      <div class="w-full">
        <slot name="description" />
      </div>
    </div>
  </div>

<!-- Mobile -->
<div class="flex flex-col md:hidden flex items-stretch rounded-xl overflow-hidden min-h-28 max-h-28 mx-2">
  <div class="w-full flex">
    <div class="w-12 bg-blue-200 flex items-center justify-center text-lg font-bold">
      <i :class="['ti', icon]"></i>
    </div>

    <div class="flex-grow bg-blue-100 px-4 flex justify-center text-lg font-medium">
      <slot name="caption" />
    </div>
  </div>

  <div class="flex-1 bg-slate-100 px-4 text-gray-800 flex items-center">
    <div class="w-full">
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
