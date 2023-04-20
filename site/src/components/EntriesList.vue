<template>

  <ul style="list-style-type: none; margin: 0; padding: 0;">
    <li v-for="entryId in entriesToShow"
        :key="entryId"
        style="margin-bottom: 0.25rem;">
      <entry-for-list :entryId="entryId"
                      :time-field="timeField"
                      :show-tags="showTags"/>
    </li>
  </ul>

  <a href="#"
     style="text-decoration: none;"
     v-if="canShowMore"
     @click.prevent="showMore()">next {{showPerPage}}</a> |

  <a href="#"
     style="text-decoration: none;"
     v-if="canShowMore"
     @click.prevent="showAll()">all</a> |

  <a href="#"
     style="text-decoration: none;"
     v-if="canHide"
     @click.prevent="hideAll()">hide</a>

</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import * as t from "@/logic/types";
import { computedAsync } from "@vueuse/core";

const properties = defineProps<{ entriesIds: Array[t.EntryId],
                                 timeField: string,
                                 showTags: boolean,
                                 showFromStart: number,
                                 showPerPage: number}>();

const showEntries = ref(properties.showFromStart);


function showMore() {
    showEntries.value += properties.showPerPage;
}

function showAll() {
    if (properties.entriesIDs == null) {
        return;
    }
    showEntries.value = properties.entriesIds.length;
}

function hideAll() {
    showEntries.value = properties.showFromStart;
}

const canHide = computed(() => {
    if (properties.entriesIds == null) {
        return false;
    }
    return showEntries.value > properties.showFromStart;
});

const entriesToShow = computed(() => {
    if (properties.entriesIds == null) {
        return [];
    }
    return properties.entriesIds.slice(0, showEntries.value);
});

const canShowMore = computed(() => {
    if (properties.entriesIds == null) {
        return false;
    }
    return showEntries.value < properties.entriesIds.length;
});


</script>

<style></style>
