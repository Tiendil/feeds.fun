<template>
  <div class="inline-block">
    <a
      href="#"
      v-if="showSwitch"
      class="pr-1"
      @click.prevent="onRevers(tag)"
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
  import {useTagsStore} from "@/stores/tags";

  const tagsStore = useTagsStore();

  const tagsStates = inject<tagsFilterState.Storage>("tagsStates");

  const properties = defineProps<{
    uid: string;
    count?: number | null;
    countMode?: string | null;
    secondaryMode?: string | null;
    showSwitch?: boolean | null;
  }>();

  const tagInfo = computed(() => {
    const tagInfo = tagsStore.tags[properties.uid];

    if (tagInfo) {
      return tagInfo;
    }

    tagsStore.requestTagInfo({tagUid: properties.uid});

    return t.noInfoTag(properties.uid);
  });

  // TODO: refactor somehow
  const mode = computed(() => {
    if (tagsStates.value.requiredTags[properties.uid]) {
      return "required";
    }

    if (tagsStates.value.excludedTags[properties.uid]) {
      return "excluded";
    }

    return "none";
  });

  const classes = computed(() => {
    const result: {[key: string]: boolean} = {
      tag: true
    };

    if (mode.value) {
      result[mode.value] = true;
    }

    if (properties.secondaryMode) {
      result[properties.secondaryMode] = true;
    }

    return result;
  });

  function onClick() {
    tagsStates.value.onTagClicked({tag: properties.uid});
  }

  function onRevers() {
    tagsStates.value.onTagReversed({tag: properties.uid});
  }

  const tooltip = computed(() => {
    // TODO: highligh the tag under the cursor
    if (properties.countMode == "tooltip" && properties.count) {
      return `articles with this tag: ${properties.count}`;
    }
    return "";
  });
</script>

<style scoped>
  .tag {
    @apply inline-block cursor-pointer p-0 mr-2 whitespace-nowrap;
  }

  /* TODO: what with required/positive and excluded/negative styles/states?
          currently they use the same colors
 */
  /* TODO: improve visual styles, make them more separatable */
  .tag.required {
    @apply text-green-700 font-bold;
  }

  .tag.excluded {
    @apply text-red-700 font-bold;
  }

  .tag.positive {
    @apply text-green-700;
  }

  .tag.negative {
    @apply text-red-700;
  }
</style>
