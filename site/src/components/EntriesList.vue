<template>
  <div>
    <template v-if="entriesToShow.length > 0">
      <ul>
        <li
          v-for="entryId in entriesToShow"
          :key="entryId"
          class="mb-1 entry-block">
          <entry-for-list
            :entryId="entryId"
            :time-field="timeField"
            :tags-count="tagsCount"
            @entry:bodyVisibilityChanged="onBodyVisibilityChanged" />
        </li>
      </ul>

      <hr />

      <simple-pagination
        :showFromStart="showFromStart"
        :showPerPage="showPerPage"
        :total="entriesIds.length"
        :counterOnNewLine="false"
        v-model:showEntries="showEntries" />
    </template>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import type * as t from "@/logic/types";
  import {computedAsync} from "@vueuse/core";

  const properties = defineProps<{
    entriesIds: Array<t.EntryId>;
    timeField: string;
    showFromStart: number;
    showPerPage: number;
    tagsCount: {[key: string]: number};
  }>();

  const emit = defineEmits(["entry:bodyVisibilityChanged"]);

  const showEntries = ref(properties.showFromStart);

  const entriesToShow = computed(() => {
    if (properties.entriesIds == null) {
      return [];
    }
    return properties.entriesIds.slice(0, showEntries.value);
  });

  function onBodyVisibilityChanged({entryId, visible}: {entryId: t.EntryId; visible: boolean}) {
    emit("entry:bodyVisibilityChanged", {entryId, visible});
  }
</script>

<style scoped>
  .entry-block {
  }

  .entry-block:not(:last-child) {
      border-bottom-width: 1px;
      @apply py-1;
  }
</style>
