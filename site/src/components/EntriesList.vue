<template>
  <div>
    <template v-if="entriesToShow.length > 0">
      <ul style="list-style-type: none; margin: 0; padding: 0">
        <li
          v-for="entryId in entriesToShow"
          :key="entryId"
          style="margin-bottom: 0.25rem">
          <entry-for-list
            :entryId="entryId"
            :time-field="timeField"
            :show-tags="showTags" />
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
    showTags: boolean;
    showFromStart: number;
    showPerPage: number;
  }>();

  const showEntries = ref(properties.showFromStart);

  const entriesToShow = computed(() => {
    if (properties.entriesIds == null) {
      return [];
    }
    return properties.entriesIds.slice(0, showEntries.value);
  });
</script>

<style></style>
