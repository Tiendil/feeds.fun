<template>
  <div>
    <template v-if="entriesToShow.length > 0">
      <ul>
        <li
          v-for="entryId in entriesToShow"
          :key="entryId"
          class="ffun-body-list-entry">
          <entry-for-list
            :show-score="showScore"
            :entryId="entryId"
            :time-field="timeField"
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
      <div
        v-if="!loading"
        class="ffun-info-common">
        No news to show.
      </div>
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
    timeField: string;
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
