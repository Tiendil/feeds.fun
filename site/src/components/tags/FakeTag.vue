<template>
<div
  :class="classes"
  :title="tooltip">
  <tag-base :tag-info="tagInfo" />
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
    uid: string;
    name: string;
    link: string|null;
    cssModifier: string;
    count: number;
  }>();

const tagInfo = computed(() => {
  return t.fakeTag({uid: properties.uid,
                    name: properties.name,
                    link: properties.link,
                    categories: []});
});

  const classes = computed(() => {
    const result: {[key: string]: boolean} = {}

    result[properties.cssModifier] = true;
    result["ffun-entry-tag"] = true;

    return result;
  });

  const tooltip = computed(() => {
    return `Articles with this tag: ${properties.count}`;
  });
</script>
