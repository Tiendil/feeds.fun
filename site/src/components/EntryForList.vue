<template>
<div class="container">

  <div style="flex-shrink: 0; width: 2rem; text-align: right; padding-right: 0.25rem;">
    <value-score :value="entry.score"
                 :entry-id="entry.id"
                 class="entity-for-list-score"/>
  </div>

  <div style="flex-grow: 1;">
    <a href="#" style="text-decoration: none;" v-if="!showBody" @click.prevent="displayBody()">&#9660;</a>
    <a href="#" style="text-decoration: none;" v-if="showBody" @click.prevent="showBody = false">&#9650;</a>

    <a :href="entry.url"
       target="_blank"
       @click="onTitleClick()">
      {{purifiedTitle}}
    </a>

    |

    <input-marker :marker="e.Marker.Read"
                  :entry-id="entryId"
                  on-text="read"
                  off-text="not read"/>

    <template v-if="showTags">
      <br/>
      <tags-list :tags="entry.tags"/>
    </template>

    <div v-if="showBody" style="display: flex; justify-content: center;">
      <div style="max-width: 50rem;">
        <h2>{{purifiedTitle}}</h2>
        <p v-if="entry.body === null">loading...</p>
        <div v-if="entry.body !== null"
             v-html="purifiedBody"/>
      </div>
    </div>
  </div>

  <div style="flex-shrink: 0; width: 1rem; left-padding: 0.25rem;">
    <value-date-time :value="timeFor()" :reversed="true"/>
  </div>

</div>
</template>

<script lang="ts" setup>
import { computed, ref } from "vue";
import * as t from "@/logic/types";
import * as e from "@/logic/enums";
import { computedAsync } from "@vueuse/core";
import DOMPurify from "dompurify";
import { useEntriesStore } from "@/stores/entries";

const entriesStore = useEntriesStore();

const properties = defineProps<{ entryId: t.EntryId,
                                 timeField: string,
                                 showTags: boolean}>();

const entry = computed(() => {
    if (properties.entryId in entriesStore.entries) {
        return entriesStore.entries[properties.entryId];
    }

    return null;
});

const showBody = ref(false);

function timeFor(): Date {
  return entry.value[properties.timeField];
}

function displayBody() {
    showBody.value = true;
    entriesStore.requestFullEntry({entryId: entry.value.id});
}

const purifiedTitle = computed(() => {
    // TODO: remove emojis?
    return DOMPurify.sanitize(entry.value.title, {ALLOWED_TAGS: []});
});

const purifiedBody = computed(() => {
    if (entry.value.body === null) {
        return "";
    }
    return DOMPurify.sanitize(entry.value.body);
});

async function onTitleClick() {
    await entriesStore.setMarker({entryId: properties.entryId, marker: e.Marker.Read});
}

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
