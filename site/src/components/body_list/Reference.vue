<template>
  <a
    :href="reference.url"
    target="_blank"
    rel="noopener noreferrer"
    :title="kindTitle"
    class="block max-w-full break-words rounded border bg-white px-1 py-1 text-sm font-medium leading-tight text-gray-900 hover:bg-gray-50">
    <template v-if="title !== null">
      <span v-html="title" />
    </template>
    <icon
      v-else
      :icon="kindIcon"
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

  const kindProperties = computed(() => {
    const value = e.ReferenceKindProperties.get(properties.reference.kind);

    if (value === undefined) {
      throw new Error(`Unknown reference kind: ${properties.reference.kind}`);
    }

    return value;
  });

  const kindTitle = computed(() => {
    return kindProperties.value.title;
  });

  const kindIcon = computed(() => {
    return kindProperties.value.icon;
  });
</script>
