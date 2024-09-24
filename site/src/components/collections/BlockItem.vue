<template>
  <div>
    <input
      class="ffun-checkbox align-top m-1"
      type="checkbox"
      :id="collection.id"
      :name="collection.name"
      :value="collection.id"
      v-model="model"
      checked />
    <label
      class="ml-2"
      :for="collection.id"
      >
      <div class="inline-block">
        {{ collection.name }}
        <p class="">{{ collection.description }}</p>
      </div>
    </label>


  </div>
</template>

<script lang="ts" setup>
  import {computed, ref} from "vue";
import type * as t from "@/logic/types";
import * as e from "@/logic/enums";
import * as api from "@/logic/api";
import {computedAsync} from "@vueuse/core";
import DOMPurify from "dompurify";
import {useEntriesStore} from "@/stores/entries";
import {useGlobalSettingsStore} from "@/stores/globalSettings";
import {useCollectionsStore} from "@/stores/collections";

const properties = defineProps<{
  collectionId: t.FeedsCollectionId;
  selectedCollections: t.FeedsCollectionId[];
}>();

const model = defineModel()

const collections = useCollectionsStore();

const collection = computed(() => collections.collections[properties.collectionId]);

</script>

<style scoped></style>
