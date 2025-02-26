<template>
  <div class="inline-block w-full">
    <a
      href="#"
      v-if="showSwitch"
      class="pr-1 ffun-tag-switch"
      :title="switchTooltip"
      @click.prevent="onRevers()"
      >⇄</a
    >
    <span
      :class="classes"
      :title="tagTooltip"
      @click.prevent="onClick()">
      <span
        v-if="showCount"
        class="pr-1"
        >[{{ count }}]</span
      >

      <tag-base :tag-info="tagInfo" />
    </span>
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
    count?: number | null;
    showCount: boolean;
    showSwitch: boolean;
    changeSource: "news_tags_filter" | "rules_tags_filter";
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

    result["ffun-filter-tag"] = true;
    result["inline-block"] = true;
    result["w-full"] = true;

    if (tagsStates.value.requiredTags[properties.uid]) {
      result["required"] = true;
    }

    if (tagsStates.value.excludedTags[properties.uid]) {
      result["excluded"] = true;
    }

    return result;
  });

  async function onClick() {
    asserts.defined(tagsStates);

    let changeInfo = tagsStates.value.onTagClicked({tag: properties.uid});

    await events.tagStateChanged({tag: properties.uid, source: properties.changeSource, ...changeInfo});
  }

  async function onRevers() {
    asserts.defined(tagsStates);

    let changeInfo = tagsStates.value.onTagReversed({tag: properties.uid});

    await events.tagStateChanged({tag: properties.uid, source: properties.changeSource, ...changeInfo});
  }

  const switchTooltip = computed(() => {
    if (tagsStates.value.requiredTags[properties.uid]) {
      return "Switch to show news without this tag";
    }

    if (tagsStates.value.excludedTags[properties.uid]) {
      return "Switch to show news with this tag";
    }

    return "Click to toggle";
  });

  const tagTooltip = computed(() => {
    if (!tagsStates.value.requiredTags[properties.uid] && !tagsStates.value.excludedTags[properties.uid]) {
      return "Show news with this tag";
    }

    return "Stop filtering by this tag";
  });
</script>
