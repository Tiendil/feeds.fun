<template>
  <div
    :class="classes"
    :title="tooltip"
    @click.prevent="onClick()">
    <slot name="start"> </slot>

    <span v-if="countMode == 'prefix'">[{{ count }}]</span>

    {{ tagInfo.name }}

    <a
      v-if="tagInfo.link"
      :href="tagInfo.link"
      target="_blank"
      @click.stop=""
      style="text-decoration: none"
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
    if (properties.countMode == "tooltip" && properties.count) {
      return `articles with the tag: ${properties.count} (${properties.uid})`;
    }
    return "";
  });
</script>

<style scoped>
  .tag {
    display: inline-block;
    cursor: pointer;
    padding: 0.1rem;
    margin-right: 0.2rem;
    white-space: nowrap;
  }

  .tag.selected {
    background-color: #ccccff;
  }

  .tag.required {
    background-color: #ccffcc;
  }

  .tag.excluded {
    background-color: #ffcccc;
  }

  .tag.positive {
    color: darkgreen;
  }

  .tag.negative {
    color: darkred;
  }
</style>
