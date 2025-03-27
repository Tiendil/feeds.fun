<template>
  <select
    class="ffun-input"
    @change="updateCollection($event)">
    <option
      v-for="collection of collections.collectionsOrdered"
      :value="collection.id"
      :selected="collection.id === collectionId">
      {{ collection.name }}
    </option>
  </select>
</template>

<script lang="ts" setup>
  import * as e from "@/logic/enums";
import type * as t from "@/logic/types";
  import {computed, ref, onUnmounted, watch, provide} from "vue";
import { useRoute, useRouter } from 'vue-router'
import {useCollectionsStore} from "@/stores/collections";

const collections = useCollectionsStore();

const route = useRoute();
const router = useRouter();

const properties = defineProps<{collectionId: t.CollectionId}>();

const collection = computed(() => collections.collections[properties.collectionId]);

function updateCollection(event: Event) {
  const target = event.target as HTMLSelectElement;

  const targetCollection = collections.collections[target.value as t.CollectionId];

    router.push({
      replace: true,
      name: route.name,
      params: {collectionSlug: targetCollection.slug,
               tags: []}
    });
  }

</script>

<style></style>
