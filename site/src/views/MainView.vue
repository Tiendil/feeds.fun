<template>
  <wide-layout>
    <div class="ffun-page-header">
      <div class="ffun-page-header-center-block">
        <page-header-external-links :show-api="false" />
      </div>
    </div>

    <hr />

    <main-block>
      <h1 class="m-0 text-5xl">Feeds Fun</h1>
      <p class="mt-2 text-2xl">Transparent Personalized News</p>
    </main-block>

    <main-header-line>
      <!-- TODO: uncomment this claim after we have some statistics on long-term users -->
      <!-- Save over <strong class="text-green-700">80%</strong> of news-browsing time by focusing on what truly matters to you -->
      Save news-browsing time by focusing on what truly matters
    </main-header-line>

    <main-block>
      <div class="max-w-xl md:mx-auto ffun-info-good text-center mx-2">
        <supertokens-login />
      </div>
    </main-block>

    <main-header-line> Smarter way to read news </main-header-line>

    <main-block>
      <main-description step="1">
        <template #caption> Subscribe to sites </template>

        <template #description>
          <p class="text-lg font-medium">Give us the site URL and we do the rest.</p>
        </template>
      </main-description>

      <main-description step="2">
        <template #caption> Get automatic tagging </template>

        <template #description>
          <div>
            <main-news-title
              class=""
              title="UFO crashes in Central Park"
              :score="null" />

            <fake-tag
              uid="ufo"
              name="ufo"
              :link="null"
              css-modifier="positive" />

            <fake-tag
              uid="news-dot-fake"
              name="news.fake"
              link="http://example.com"
              css-modifier="negative" />

            <fake-tag
              uid="new-york"
              name="new-york"
              :link="null"
              css-modifier="positive" />

            <fake-tag
              uid="space-exploration"
              name="space-exploration"
              :link="null"
              css-modifier="positive" />
          </div>
        </template>
      </main-description>

      <main-description step="3">
        <template #caption> Create scoring rules </template>

        <template #description>
          <div class="grid grid-cols-2 justify-items-start">
            <div class="">
              <fake-tag
                uid="sci-fi"
                name="sci-fi"
                :link="null"
                css-modifier="positive" />

              <icon
                icon="arrow-right"
                size="small"
                class="mx-0.5" />

              <span class="inline-block align-middle cursor-default text-purple-700 text-lg md:text-xl">+5</span>
            </div>

            <div class="">
              <fake-tag
                uid="news-dot-fake"
                name="news.fake"
                link="http://example.com"
                css-modifier="negative" />

              <icon
                icon="arrow-right"
                size="small"
                class="mx-0.5" />

              <span class="inline-block align-middle cursor-default text-purple-700 text-lg md:text-xl">-55</span>
            </div>

            <div class="">
              <fake-tag
                uid="ufo"
                name="ufo"
                :link="null"
                css-modifier="positive" />

              <icon
                icon="plus"
                size="small"
                class="mx-0.5" />

              <fake-tag
                uid="new-york"
                name="new-york"
                :link="null"
                css-modifier="positive" />

              <icon
                icon="arrow-right"
                size="small"
                class="mx-0.5" />

              <span class="inline-block align-middle cursor-default text-purple-700 text-lg md:text-xl">+8</span>
            </div>

            <div class="">
              <fake-tag
                uid="space-exploration"
                name="space-exploration"
                :link="null"
                css-modifier="positive" />

              <icon
                icon="arrow-right"
                size="small"
                class="mx-0.5" />

              <span class="inline-block align-middle cursor-default text-purple-700 text-lg md:text-xl">+21</span>
            </div>
          </div>
        </template>
      </main-description>

      <main-description step="4">
        <template #caption> Read what matters </template>

        <template #description>
          <div class="justify-items-start">
            <main-news-title
              title="New mission on Mars"
              :score="21" />

            <main-news-title
              class="opacity-75"
              title="Sci-fi novel about UFO in New Yourk"
              :score="13" />

            <div class="opacity-65 block justify-self-center">
              <icon icon="dots" />
            </div>

            <main-news-title
              class="opacity-55"
              title="UFO crashes in Central Park"
              :score="-26" />
          </div>
        </template>
      </main-description>
    </main-block>

    <main-header-line v-if="settings.hasCollections">
      Curated news collections <br class="md:hidden" />for easy start
    </main-header-line>

    <main-block v-if="settings.hasCollections">
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <template
          v-for="collectionId in collections.collectionsOrder"
          :key="collectionId">
          <main-item v-if="collections.collections[collectionId].showOnMain">
            <template #caption>
              {{ collections.collections[collectionId].name }}
            </template>

            <template #description>
              <div>{{ collections.collections[collectionId].description }}</div>
              <div class="mt-2">
                <a
                  :href="publicCollectionHref(collections.collections[collectionId].slug)"
                  class="ffun-normal-link pt-4">
                  Read the news
                </a>
              </div>
            </template>
          </main-item>
        </template>
      </div>
    </main-block>

    <main-header-line> Here, take a peek </main-header-line>
    <div class="text-center p-5">
      <img
        class="border-2 rounded border-slate-300 mx-auto"
        src="/news-filtering-example.png"
        alt="News filtering example" />
    </div>
  </wide-layout>
</template>

<script lang="ts" setup>
  import {computed, ref, onUnmounted, watch, provide} from "vue";
  import * as settings from "@/logic/settings";
  import {useRouter, RouterLink, RouterView} from "vue-router";
  import {useCollectionsStore} from "@/stores/collections";
  import * as t from "@/logic/types";

  const router = useRouter();
  const collections = useCollectionsStore();

  provide("eventsViewName", "main");

  function publicCollectionHref(collectionSlug: t.CollectionSlug) {
    return router.resolve({name: "public-collection", params: {collectionSlug: collectionSlug}}).href;
  }
</script>
