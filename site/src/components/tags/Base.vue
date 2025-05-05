<template>
  <span>
    {{ tagInfo.name }}

    <a
      v-if="tagInfo.link"
      :href="tagInfo.link"
      target="_blank"
      @click.stop=""
      rel="noopener noreferrer">
      <icon icon="external-link" size="small"/>
    </a>
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
    tagInfo: t.TagInfo;
  }>();
</script>
