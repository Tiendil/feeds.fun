<template>
<div style="display: flex;">
  <div style="flex-shrink: 0; width: 2rem; text-align: right; padding-right: 0.25rem;">
    <value-score :value="entry.score" class="entity-for-list-score"/>
  </div>

  <div style="flex-grow: 1;">
    <a href="#" style="text-decoration: none;" v-if="!showBody" @click="showBody = true">&#9660;</a>
    <a href="#" style="text-decoration: none;" v-if="showBody" @click="showBody = false">&#9650;</a>

    <value-url :value="entry.url" :text="entry.title" class="entity"/>

    <template v-if="showTags">
      <br/>
      <tags-list :tags="entry.tags"/>
    </template>

    <template v-if="showBody">
      <br/>
      <h2>{{entry.title}}</h2>
      <p v-if="fullEntry === null">loading...</p>
      <div v-if="fullEntry !== null" v-html="purifiedBody"/>
    </template>
  </div>

  <div style="flex-shrink: 0; width: 1rem; left-padding: 0.25rem;">
    <value-date-time :value="timeFor(entry)" :reversed="true"/>
  </div>

</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import * as t from "@/logic/types";
import { computedAsync } from "@vueuse/core";
import * as api from "@/logic/api";
import DOMPurify from "dompurify";

const properties = defineProps<{ entry: t.Entry,
                                 timeField: string,
                                 showTags: boolean}>();

const showBody = ref(false);

function timeFor(entry: t.Entry): Date {
  return entry[properties.timeField];
}

const fullEntry = computedAsync(async () => {
    return await api.getEntry({entryId: properties.entry.id});
}, null);


const purifiedBody = computed(() => {
    if (fullEntry.value === null) {
        return "";
    }
    return DOMPurify.sanitize(fullEntry.value.body);
});

</script>

<style></style>
