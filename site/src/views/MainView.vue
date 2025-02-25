<template>
  <wide-layout>

    <header class="bg-blue-500 text-white p-5 text-center">
      <h1 class="m-0 text-5xl">Feeds Fun</h1>
      <p class="mt-2 text-2xl">Personalized News for Professionals</p>
    </header>

    <div class="bg-slate-200 text-center p-5">
      <p class="text-3xl font-medium">
        Save over <strong class="text-green-700">80%</strong> of news-browsing time by focusing on what truly matters to you
      </p>
    </div>

    <div class="max-w-3xl mx-auto mt-4">
      <div class="ffun-info-good">
        <h2 class="my-0">Register without password</h2>
        <supertokens-login />
      </div>
    </div>

    <div class="bg-white text-center p-5">
      <h1 class="m-0 text-3xl mb-4">How Feeds Fun Works</h1>

      <div class="max-w-3xl mx-auto space-y-6">

        <main-description icon="ti-number-1">
          <template #caption>
            Subscribe to news
          </template>

          <template #description>
            Most sites provide RSS or ATOM feeds of their updates, that anyone can subscribe to.
          </template>
        </main-description>

        <main-description icon="ti-number-2">
          <template #caption>
            Automatic tagging
          </template>

          <template #description>
            <!-- <p>Feeds Fun automatically tags news articles based on their content—people, places, topics, games, and more.</p> -->

            <h3>UFO Crashes in Central Park</h3>

            <fake-tag
              uid="ufo"
              name="ufo"
              :link="null"
              css-modifier="positive"
              :count="100500" />

            <fake-tag
              uid="news-dot-fake"
              name="news.fake"
              link="http://example.com"
              css-modifier="negative"
              :count="13" />

            <fake-tag
              uid="new-york"
              name="new-york"
              :link="null"
              css-modifier="positive"
              :count="3" />

            <fake-tag
              uid="space-exploration"
              name="space-exploration"
              :link="null"
              css-modifier="positive"
              :count="31" />

          </template>
        </main-description>

        <main-description icon="ti-number-3">
          <template #caption>
            Score tags
          </template>

          <template #description>
            Set rules to rank news. Want Python over Java? No politics? You decide what comes first.
          </template>
        </main-description>

        <main-description icon="ti-number-4">
          <template #caption>
            Read what matters
          </template>

          <template #description>
            Feeds Fun filters and sorts news based on your rules, so the most relevant stories are always on top.
          </template>
        </main-description>

        <main-description icon="ti-number-5">
          <template #caption>
            Full transparency
          </template>

          <template #description>
            See exactly how your rules shape your feed—no black boxes, no hidden algorithms. Check our
          </template>
        </main-description>

      </div>
    </div>

    <div class="bg-slate-200 text-center p-5">
      <p class="text-3xl font-medium">
        Check our collections TODO
      </p>
    </div>

    <div class="bg-white text-center p-5">
      <h1 class="m-0 text-3xl mb-4">How Feeds Looks Like</h1>

      <img
        class="border-2 rounded border-slate-300 mx-auto"
        src="/news-filtering-example.png"
        alt="News filtering example" />

    </div>
  </wide-layout>
</template>

<script lang="ts" setup>
  import * as settings from "@/logic/settings";
</script>
