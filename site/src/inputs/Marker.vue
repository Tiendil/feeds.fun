<template>
  <div>
    <template v-if="hasMarker">
      <a
        href="#"
        @click.prevent="unmark()">
        <slot name="marked" />
      </a>
    </template>

    <template v-else>
      <a
        href="#"
        @click.prevent="mark()">
        <slot name="unmarked" />
      </a>
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

<style scoped></style>
