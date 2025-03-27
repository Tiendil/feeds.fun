<template>
  <div class="ffun-info-good">
        <h4>Hi there!</h4>

        <p>
          Welcome to <strong>Feeds Fun</strong> and our curated <strong>{{collection.name}}</strong> news collection!
        </p>

        <p>
          <strong>Feeds Fun</strong> ranks news based on tags, so you always see what matters most. We offer public collections to showcase our tagging system in action. Hope you'll enjoy it!
        </p>

        <p v-if="tag1Uid && tag2Uid">
          Try out the tag filters on the left, for example, filter news by tag
          <entry-tag
            :uid="tag1Uid"
            css-modifier="neutral"
            :count="tag1Count" />

          or even by a more specific tag

          <entry-tag
            :uid="tag2Uid"
            css-modifier="neutral"
            :count="tag2Count" />
        </p>

        <p>
          If you like the results, <a :href="router.resolve({name: 'main'}).href">register</a> to create your own scoring rules and automatically prioritize the news you’re most interested in.
        </p>

        <p>
          You can find more about scoring rules on the <a :href="router.resolve({name: 'main'}).href">main page</a>.
        </p>

        <p><strong>All news in this collection is always up-to-date and tagged.</strong>
        </p>

  </div>
</template>

<script lang="ts" setup>
  import {computed} from "vue";
import { useRouter } from 'vue-router'
import type * as t from "@/logic/types";
import {useCollectionsStore} from "@/stores/collections";

const properties = defineProps<{
  tag1Uid: string | null;
  tag1Count: number;
  tag2Uid: string | null;
  tag2Count: number;
  collectionId: t.CollectionId;
}>();

const router = useRouter();

const collections = useCollectionsStore();

const collection = computed(() => {
  return collections.collections[properties.collectionId];
});


</script>

<style></style>
