<template>
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
</template>

<script lang="ts" setup>
  import * as t from "@/logic/types";
  import {computed, ref} from "vue";
  import {useTagsStore} from "@/stores/tags";

  const tagsStore = useTagsStore();

  const properties = defineProps<{
    uid: string;
    count?: number | null;
    countMode?: string | null;
    mode?: string | null;
  }>();

  const tagInfo = computed(() => {
    const tagInfo = tagsStore.tags[properties.uid];

    if (tagInfo) {
      return tagInfo;
    }

    tagsStore.requestTagInfo({tagUid: properties.uid});

    return t.noInfoTag(properties.uid);
  });

  const emit = defineEmits(["tag:clicked"]);

  const classes = computed(() => {
    const result: {[key: string]: boolean} = {
      tag: true
    };

    if (properties.mode) {
      result[properties.mode] = true;
    }

    return result;
  });

  function onClick() {
    emit("tag:clicked", properties.uid);
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
  .tag.required {
    @apply text-green-700;
  }

  .tag.excluded {
    @apply text-red-700;
  }

  .tag.positive {
    @apply text-green-700;
  }

  .tag.negative {
    @apply text-red-700;
  }
</style>
