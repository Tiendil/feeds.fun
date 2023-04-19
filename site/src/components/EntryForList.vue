<template>
<div class="container">

  <div style="flex-shrink: 0; width: 2rem; text-align: right; padding-right: 0.25rem;">
    <value-score :value="entry.score"
                 :entry-id="entry.id"
                 class="entity-for-list-score"/>
  </div>

  <div style="flex-grow: 1;">
    <a href="#" style="text-decoration: none;" v-if="!showBody" @click.prevent="showBody = true">&#9660;</a>
    <a href="#" style="text-decoration: none;" v-if="showBody" @click.prevent="showBody = false">&#9650;</a>

    <value-url :value="entry.url" :text="entry.title" class="entity"/>

    <template v-if="showTags">
      <br/>
      <tags-list :tags="entry.tags"/>
    </template>

    <div v-if="showBody" style="display: flex; justify-content: center;">
      <div style="max-width: 50rem;">
        <h2>{{entry.title}}</h2>
        <p v-if="fullEntry === null">loading...</p>
        <div v-if="fullEntry !== null"
             v-html="purifiedBody"/>
      </div>
    </div>
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
    if (!showBody.value) {
        return null;
    }
    const entries = await api.getEntriesByIds({ids: [properties.entry.id]});

    return entries[0];
}, null);


const purifiedBody = computed(() => {
    if (fullEntry.value === null) {
        return "";
    }
    return DOMPurify.sanitize(fullEntry.value.body);
    });




</script>

<style scoped>
  .container {
      display: flex;
  }

  .container :deep(img) {
     max-width: 100%;
     height: auto;
  }
</style>
