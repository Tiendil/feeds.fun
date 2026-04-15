<template>
  <a
    :href="reference.url"
    target="_blank"
    rel="noopener noreferrer"
    :title="semanticTitle"
    class="block max-w-full break-words rounded border bg-white px-1 py-1 text-sm font-medium leading-tight text-gray-900 hover:bg-gray-50">
    <template v-if="title !== null">
      <span v-html="title"/>
    </template>
    <icon
      v-else
      :icon="semanticIcon"
      size="small" />
  </a>
</template>

<script lang="ts" setup>
  import {computed} from "vue";
  import type * as t from "@/logic/types";
  import * as e from "@/logic/enums";
  import * as utils from "@/logic/utils";

  const properties = defineProps<{
    reference: t.Reference;
  }>();

  const title = computed(() => {
    const value = utils.purifyTitle({raw: properties.reference.title, default_: ""});

    if (value.length === 0) {
      return null;
    }

    return value;
  });

  const semanticProperties = computed(() => {
    const value = e.ReferenceSemanticsProperties.get(properties.reference.semantics);

    if (value === undefined) {
      throw new Error(`Unknown reference semantics: ${properties.reference.semantics}`);
    }

    return value;
  });

  const semanticTitle = computed(() => {
    return semanticProperties.value.title;
  });

  const semanticIcon = computed(() => {
    return semanticProperties.value.icon;
  });
</script>
