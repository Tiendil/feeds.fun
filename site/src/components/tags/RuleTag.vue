<template>
  <div
    :class="classes"
    @click.prevent="onClick()">
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

  const tagsStore = useTagsStore();

  const tagsStates = inject<Ref<tagsFilterState.Storage>>("tagsStates");

  asserts.defined(tagsStates);

  const properties = defineProps<{
    uid: string;
    cssModifier: string;
  }>();

  const tagInfo = computed(() => {
    const tagInfo = tagsStore.tags[properties.uid];

    if (tagInfo) {
      return tagInfo;
    }

    tagsStore.requestTagInfo({tagUid: properties.uid});

    return t.noInfoTag(properties.uid);
  });

  const classes = computed(() => {
    const result: {[key: string]: boolean} = {};

    result[properties.cssModifier] = true;
    result["ffun-entry-tag"] = true;

    if (tagsStates.value.requiredTags[properties.uid]) {
      result["required"] = true;
    }

    if (tagsStates.value.excludedTags[properties.uid]) {
      result["excluded"] = true;
    }

    return result;
  });

  const changeSource = "rule_record";

  async function onClick() {
    asserts.defined(tagsStates);

    let changeInfo = tagsStates.value.onTagClicked({tag: properties.uid});

    await events.tagStateChanged({tag: properties.uid, source: changeSource, ...changeInfo});
  }
</script>
