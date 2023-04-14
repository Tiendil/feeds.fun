<template>

  <ul style="list-style-type: none; margin: 0; padding: 0;">
    <li v-for="entry in entriesToShow"
        :key="entry.id"
        style="margin-bottom: 0.25rem;">
      <entry-for-list :entry="entry"
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
     @click.prevent="showAll()">all</a>

</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import * as t from "@/logic/types";
import { computedAsync } from "@vueuse/core";

const properties = defineProps<{ entries: Array[t.Entry],
                                 timeField: string,
                                 showTags: boolean,
                                 showFromStart: number,
                                 showPerPage: number}>();

const showEntries = ref(properties.showFromStart);


function showMore() {
    showEntries.value += properties.showPerPage;
}

function showAll() {
    if (properties.entries == null) {
        return;
    }
    showEntries.value = properties.entries.length;
}

const entriesToShow = computed(() => {
    if (properties.entries == null) {
        return [];
    }
    return properties.entries.slice(0, showEntries.value);
});

const canShowMore = computed(() => {
    if (properties.entries == null) {
        return false;
    }
    return showEntries.value < properties.entries.length;
});

function timeFor(entry: t.Entry): Date {
  return entry[properties.timeField];
}

</script>

<style></style>
