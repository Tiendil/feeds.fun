import {computed, ref, watch} from "vue";
import {useRouter} from "vue-router";
import {defineStore} from "pinia";

import type * as t from "@/logic/types";
import * as e from "@/logic/enums";
import * as api from "@/logic/api";
import {Timer} from "@/logic/timer";
import {computedAsync} from "@vueuse/core";


export const useCollectionsStore = defineStore("collectionsStore", () => {

  const collections = computedAsync(async () => {
    const collectionsList = await api.getCollections();

    const collections = {};

    for (const collection of collectionsList) {
      collections[collection.id] = collection;
    }

    return collections;
  }, {});

  const collectionsOrder = computed(() => {
    const order = Object.keys(collections.value);

    order.sort((a, b) => {
      return collections.value[a].guiOrder - collections.value[b].guiOrder;
    });

    return order;
  });

  return {
    collections,
    collectionsOrder
  };
});
