<template>
  <wide-layout>

    <header class="bg-blue-500 text-white p-5 text-center">
      <h1 class="m-0 text-4xl">Feeds Fun</h1>
      <p class="mt-2 text-xl">Personalized News for Professionals</p>
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

        <div class="flex items-stretch bg-white rounded-xl overflow-hidden">
          <!-- Number div -->
          <div class="w-12 bg-blue-600 text-white flex items-center justify-center text-2xl font-bold">
            <i class="ti ti-number-1"></i>
          </div>
          <!-- Caption div -->
          <div class="w-1/3 bg-blue-500 text-white p-6 flex items-center text-lg font-bold">
            Subscribe to feeds
          </div>
          <!-- Description div -->
          <div class="flex-1 bg-gray-100 p-6 text-gray-800 flex items-center">
            Stay updated with news from major sites like Reddit, ArXiv.org, Medium, or even your friends’ blogs—all in one place.
          </div>
        </div>

        <div class="flex items-stretch bg-white rounded-xl overflow-hidden">
          <div class="w-12 bg-blue-600 text-white flex items-center justify-center text-2xl font-bold">
            <i class="ti ti-number-2"></i>
          </div>
          <div class="w-1/3 bg-blue-500 text-white p-6 flex items-center text-lg font-bold">
            Automatic tagging
          </div>
          <div class="flex-1 bg-gray-100 p-6 text-gray-800 flex items-center">
            Feeds Fun automatically tags news articles based on their content—people, places, topics, games, and more.
          </div>
        </div>

        <div class="flex items-stretch bg-white rounded-xl overflow-hidden">
          <div class="w-12 bg-blue-600 text-white flex items-center justify-center text-2xl font-bold">
            <i class="ti ti-number-3"></i>
          </div>
          <div class="w-1/3 bg-blue-500 text-white p-6 flex items-center text-lg font-bold">
            Score your news
          </div>
          <div class="flex-1 bg-gray-100 p-6 text-gray-800 flex items-center">
            Set rules to rank news. Want Python over Java? No politics? You decide what comes first.
          </div>
        </div>

        <div class="flex items-stretch bg-white rounded-xl overflow-hidden">
          <div class="w-12 bg-blue-600 text-white flex items-center justify-center text-2xl font-bold">
            <i class="ti ti-number-4"></i>
          </div>
          <div class="w-1/3 bg-blue-500 text-white p-6 flex items-center text-lg font-bold">
            Read what matters
          </div>
          <div class="flex-1 bg-gray-100 p-6 text-gray-800 flex items-center">
            Feeds Fun filters and sorts news based on your rules, so the most relevant stories are always on top.
          </div>
        </div>

        <div class="flex items-stretch bg-white rounded-xl overflow-hidden">
          <div class="w-12 bg-blue-600 text-white flex items-center justify-center text-2xl font-bold">
            <i class="ti ti-number-5"></i>
          </div>
          <div class="w-1/3 bg-blue-500 text-white p-6 flex items-center text-lg font-bold">
            Full transparency
          </div>
          <div class="flex-1 bg-gray-100 p-6 text-gray-800 flex items-center">
            See exactly how your rules shape your feed—no black boxes, no hidden algorithms. Check our
            <external-url url="https://github.com/Tiendil/feeds.fun" text="source code"/>.
          </div>
        </div>

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
