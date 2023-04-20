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

    <value-url :value="entry.url" :text="purifiedTitle" class="entity"/>

    |

    <input-marker :marker="e.Marker.Read"
                  :entry="entry"
                  on-text="read"
                  off-text="not read"/>

    <template v-if="showTags">
      <br/>
      <tags-list :tags="entry.tags"/>
    </template>

    <div v-if="showBody" style="display: flex; justify-content: center;">
      <div style="max-width: 50rem;">
        <h2>{{entry.title}}</h2>
        <p v-if="entry.body === null">loading...</p>
        <div v-if="entry.body !== null"
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
import * as e from "@/logic/enums";
import { computedAsync } from "@vueuse/core";
import * as api from "@/logic/api";
import DOMPurify from "dompurify";
import { useEntriesStore } from "@/stores/entries";

const entriesStore = useEntriesStore();

const properties = defineProps<{ entryId: t.EntryId,
                                 timeField: string,
                                 showTags: boolean}>();

const entry = computed(() => entriesStore.entries.value[properties.entryId]);

const showBody = ref(false);

function timeFor(entry: t.Entry): Date {
  return entry.value[properties.timeField];
}

const purifiedTitle = computed(() => {
    // TODO: remove emojis?
    return DOMPurify.sanitize(entry.value.title, {ALLOWED_TAGS: []});
});

const purifiedBody = computed(() => {
    if (entry.value.body === null) {
        entriesStore.requestFullEntry(entry.value.id);
        return "";
    }
    return DOMPurify.sanitize(entry.value.body);
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
