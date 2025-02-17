<template>
  <div class="inline-block">
    <a
      href="#"
      v-if="showSwitch"
      class="pr-1"
      @click.prevent="onRevers()"
      >⇄</a
    >
    <div
      :class="classes"
      :title="tooltip"
      @click.prevent="onClick()">
      <span v-if="countMode == 'prefix'">[{{ count }}]</span>

      {{ tagInfo.name }}

      <a
        v-if="tagInfo.link"
        :href="tagInfo.link"
        target="_blank"
        @click.stop=""
        rel="noopener noreferrer">
        &#8599;
      </a>
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

  const tagsStore = useTagsStore();

  const tagsStates = inject<Ref<tagsFilterState.Storage>>("tagsStates");

  asserts.defined(tagsStates);

  const properties = defineProps<{
    uid: string;
    count?: number | null;
    countMode?: string | null;
    secondaryMode?: string | null;
    showSwitch?: boolean | null;
    changeSource: events.TagChangeSource;
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
    const result: {[key: string]: boolean} = {}

    result[properties.cssModifier] = true;
    result["ffun-tag"] = true;

    if (tagsStates.value.requiredTags[properties.uid]) {
      result["required"] = true;
    }

    if (tagsStates.value.excludedTags[properties.uid]) {
      result["excluded"] = true;
    }

    if (properties.secondaryMode) {
      result[properties.secondaryMode] = true;
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

  const tooltip = computed(() => {
    if (properties.countMode == "tooltip" && properties.count) {
      return `articles with this tag: ${properties.count}`;
    }
    return "";
  });
</script>
