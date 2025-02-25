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

    <div class="max-w-lg mx-auto mt-4">
      <div class="ffun-info-good">
        <supertokens-login />
      </div>
    </div>

    <div class="bg-white text-center p-5">
      <h1 class="m-0 text-3xl mb-4">How Feeds Fun Works</h1>

      <div class="max-w-3xl mx-auto space-y-6">

        <main-description icon="ti-number-1">
          <template #caption>
            Subscribe to feeds
          </template>

          <template #description>
            Stay updated with news from major sites like Reddit, ArXiv.org, Medium, or even your friends’ blogs—all in one place.
          </template>
        </main-description>

        <main-description icon="ti-number-2">
          <template #caption>
            Automatic tagging
          </template>

          <template #description>
            Feeds Fun automatically tags news articles based on their content—people, places, topics, games, and more.
          </template>
        </main-description>

        <main-description icon="ti-number-3">
          <template #caption>
            Score your news
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
