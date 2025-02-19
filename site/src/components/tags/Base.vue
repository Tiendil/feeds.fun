<template>
  <span>
      {{ tagInfo.name }}

      <a
        v-if="tagInfo.link"
        :href="tagInfo.link"
        target="_blank"
        @click.stop=""
        rel="noopener noreferrer">
        &#8599;
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

  const tagsStore = useTagsStore();

  const tagsStates = inject<Ref<tagsFilterState.Storage>>("tagsStates");

  asserts.defined(tagsStates);

  const properties = defineProps<{
    uid: string;
  }>();

  const tagInfo = computed(() => {
    const tagInfo = tagsStore.tags[properties.uid];

    if (tagInfo) {
      return tagInfo;
    }

    tagsStore.requestTagInfo({tagUid: properties.uid});

    return t.noInfoTag(properties.uid);
  });

</script>
