<template>
  <div>
    <template v-if="entriesToShow.length > 0">
      <div class="mb-1 flex border-b pb-1 text-xs text-gray-500">
        <div class="mr-2 w-4 flex-shrink-0" />

        <div
          v-if="showScore"
          class="w-8 flex-shrink-0 pr-1 text-center">
          Score
        </div>

        <div class="w-8 flex-shrink-0 pr-1" />

        <div class="flex-grow">News</div>

        <div class="w-16 flex-shrink-0 text-right">Published</div>
      </div>

      <ul>
        <li
          v-for="entryId in entriesToShow"
          :key="entryId"
          class="ffun-body-list-entry">
          <entry-for-list
            :show-score="showScore"
            :entryId="entryId"
            :tags-count="tagsCount" />
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

    <template v-else>
      <ui-empty-state v-if="!loading"> No news to show. </ui-empty-state>
    </template>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import type * as t from "@/logic/types";
  import {computedAsync} from "@vueuse/core";

  const properties = defineProps<{
    loading: boolean;
    entriesIds: Array<t.EntryId>;
    showFromStart: number;
    showPerPage: number;
    showScore: boolean;
    tagsCount: {[key: string]: number};
  }>();

  const showEntries = ref(properties.showFromStart);

  const entriesToShow = computed(() => {
    if (properties.entriesIds == null) {
      return [];
    }
    return properties.entriesIds.slice(0, showEntries.value);
  });
</script>
