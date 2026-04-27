<template>
  <div class="flex my-1">
    <div
      ref="bodyCard"
      class="max-w-3xl flex-1 bg-white border rounded p-4">
      <h2
        v-if="url"
        class="mt-0 mb-0"
        ><a
          :href="url"
          target="_blank"
          @click="emit('body-title-clicked')"
          v-html="title" />
      </h2>

      <body-list-references
        v-if="references.length > 0"
        :references="references" />

      <p
        v-if="loading"
        class="mt-4"
        >loading…</p
      >

      <div
        v-else-if="coverReference !== null || text"
        class="mt-4">
        <body-list-entry-cover
          v-if="coverReference !== null"
          :reference="coverReference"
          :container-width="bodyCardWidth" />

        <div
          v-if="text"
          class="prose max-w-none"
          v-html="text" />

        <div
          v-if="hasImageCover"
          class="clear-both" />
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
  import {computed, useTemplateRef} from "vue";
  import {useElementSize} from "@vueuse/core";
  import * as e from "@/logic/enums";
  import type * as t from "@/logic/types";

  const properties = defineProps<{
    url: string | null;
    title: string | null;
    loading: boolean;
    text: string | null;
    references: t.Reference[];
  }>();

  const emit = defineEmits(["body-title-clicked"]);
  const bodyCard = useTemplateRef("bodyCard");
  const {width: bodyCardWidth} = useElementSize(bodyCard);

  const coverReference = computed(() => {
    for (const reference of properties.references) {
      if (reference.kind !== e.ReferenceKind.Video) {
        continue;
      }

      if (reference.youtubeId() !== null) {
        return reference;
      }
    }

    for (const reference of properties.references) {
      if (reference.kind === e.ReferenceKind.Image) {
        return reference;
      }
    }

    return null;
  });

  const hasImageCover = computed(() => {
    return coverReference.value?.kind === e.ReferenceKind.Image;
  });
</script>
