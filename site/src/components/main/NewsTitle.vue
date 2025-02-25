<template>
  <span class="block text-lg">

    <span v-if="score" class="cursor-pointer text-purple-700 inline-block w-12">{{score}}</span>

    <span class="font-bold">{{title}}</span>
  </span>
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
    title: string;
    score: number|null;
  }>();

</script>
