<template>
  <div style="display: inline-block">
    <template v-if="hasMarker">
      <a
        href="#"
        class="marked"
        @click.prevent="unmark()"
        >{{ onText }}</a
      >
    </template>

    <template v-else>
      <a
        href="#"
        class="unmarked"
        @click.prevent="mark()"
        >{{ offText }}</a
      >
    </template>
  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
  import * as api from "@/logic/api";
  import * as e from "@/logic/enums";
  import type * as t from "@/logic/types";
  import {useEntriesStore} from "@/stores/entries";

  const entriesStore = useEntriesStore();

  const properties = defineProps<{
    marker: e.Marker;
    entryId: t.EntryId;
    onText: string;
    offText: string;
  }>();

  const hasMarker = computed(() => {
    return entriesStore.entries[properties.entryId].hasMarker(properties.marker);
  });

  async function mark() {
    await entriesStore.setMarker({
      entryId: properties.entryId,
      marker: properties.marker
    });
  }

  async function unmark() {
    await entriesStore.removeMarker({
      entryId: properties.entryId,
      marker: properties.marker
    });
  }
</script>

<style scoped>
  .marked {
    color: #2e8f2e;
    font-weight: bold;
    text-decoration: none;
  }

  .unmarked {
    color: purple;
    /* font-weight: bold; */
    text-decoration: none;
  }
</style>
