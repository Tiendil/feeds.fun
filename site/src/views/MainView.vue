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

    <div class="bg-white text-center p-5">
      <h1 class="m-0 text-3xl my-5">How Feeds Fun Works</h1>

<div class="max-w-3xl mx-auto space-y-6">

  <div class="flex items-stretch bg-white rounded-xl overflow-hidden">
    <div class="w-1/3 bg-blue-500 text-white p-6 flex items-center justify-center text-lg font-bold space-x-2">
      <i class="ti ti-number-1 text-3xl"></i>
      <span>Subscribe to feeds</span>
    </div>
    <div class="w-2/3 bg-gray-100 p-6 text-gray-800 flex items-center">
      Stay updated with news from major sites like Reddit, ArXiv.org, Medium, or even your friends’ blogs—all in one place.
    </div>
  </div>

  <div class="flex items-stretch bg-white rounded-xl overflow-hidden">
    <div class="w-1/3 bg-blue-500 text-white p-6 flex items-center justify-center text-lg font-bold space-x-2">
      <i class="ti ti-number-2 text-3xl"></i>
      <span>Automatic tagging</span>
    </div>
    <div class="w-2/3 bg-gray-100 p-6 text-gray-800 flex items-center">
      Feeds Fun automatically tags news articles based on their content—people, places, topics, games, and more.
    </div>
  </div>

  <div class="flex items-stretch bg-white rounded-xl overflow-hidden">
    <div class="w-1/3 bg-blue-500 text-white p-6 flex items-center justify-center text-lg font-bold space-x-2">
      <i class="ti ti-number-3 text-3xl"></i>
      <span>Score your news</span>
    </div>
    <div class="w-2/3 bg-gray-100 p-6 text-gray-800 flex items-center">
      Set rules to rank news. Want Python over Java? No politics? You decide what comes first.
    </div>
  </div>

  <div class="flex items-stretch bg-white rounded-xl overflow-hidden">
    <div class="w-1/3 bg-blue-500 text-white p-6 flex items-center justify-center text-lg font-bold space-x-2">
      <i class="ti ti-number-4 text-3xl"></i>
      <span>Read what matters</span>
    </div>
    <div class="w-2/3 bg-gray-100 p-6 text-gray-800 flex items-center">
      Feeds Fun filters and sorts news based on your rules, so the most relevant stories are always on top.
    </div>
  </div>

  <div class="flex items-stretch bg-white rounded-xl overflow-hidden">
    <div class="w-1/3 bg-blue-500 text-white p-6 flex items-center justify-center text-lg font-bold space-x-2">
      <i class="ti ti-number-5 text-3xl"></i>
      <span>Full transparency</span>
    </div>
    <div class="w-2/3 bg-gray-100 p-6 text-gray-800 flex items-center">
      See exactly how your rules shape your feed—no black boxes, no hidden algorithms. Check our
      <external-url url="https://github.com/Tiendil/feeds.fun" text="source code"/>.
    </div>
  </div>

</div>


      <!-- <div class="max-w-5xl mx-auto flex flex-wrap justify-center gap-6 lg:gap-8"> -->
      <!--   <div class="bg-slate-100 p-6 rounded-md w-72 text-left"> -->
      <!--   <h3 class="text-lg font-bold mb-2">Smart Tagging</h3> -->
      <!--   <p class="text-sm"> -->
      <!--     Automatically assigns relevant tags to news articles for better -->
      <!--     organization. -->
      <!--   </p> -->
      <!-- </div> -->
      <!-- <div class="bg-slate-100 p-6 rounded-md w-72 text-left"> -->
      <!--   <h3 class="text-lg font-bold mb-2">Custom Scoring</h3> -->
      <!--   <p class="text-sm"> -->
      <!--     Create rules to score news based on your preferred tags and topics. -->
      <!--   </p> -->
      <!-- </div> -->
      <!-- <div class="bg-slate-100 p-6 rounded-md w-72 text-left"> -->
      <!--   <h3 class="text-lg font-bold mb-2">Filtered Feed</h3> -->
      <!--   <p class="text-sm"> -->
      <!--     Sort and filter news so you only read the most important stories. -->
      <!--   </p> -->
      <!-- </div> -->
      <!-- <div class="bg-slate-100 p-6 rounded-md w-72 text-left"> -->
      <!--   <h3 class="text-lg font-bold mb-2">Curated Collections</h3> -->
      <!--   <p class="text-sm"> -->
      <!--     Explore handpicked thematic collections of feeds for quick insights. -->
      <!--   </p> -->
      <!-- </div> -->
      <!-- <div class="bg-slate-100 p-6 rounded-md w-72 text-left"> -->
      <!--   <h3 class="text-lg font-bold mb-2">Transparent &amp; Open</h3> -->
      <!--   <p class="text-sm"> -->
      <!--     Open source, self-hosted – no hidden algorithms or ads. -->
      <!--   </p> -->
      <!-- </div> -->
    <!-- </div> -->

    </div>

    <div class="max-w-lg mx-auto">
      <div class="ffun-info-good">
        <supertokens-login />
      </div>

      <h2>News reader with tags</h2>

      <ul class="list-disc list-inside text-left">
        <li>Reader automatically assigns tags to news.</li>
        <li>You create rules to score news by tags.</li>
        <li>Filter and sort news how you want ⇒ read only what you want.</li>
      </ul>

      <h2>Curated collections of feeds</h2>

      <ul class="list-disc list-inside text-left">
        <li>We handpick the most interesting feeds into thematic collections.</li>
        <li>Feeds in the collections are tagged for free.</li>
      </ul>

      <h2>You are in control</h2>

      <ul class="list-disc list-inside text-left">
        <li
          ><a
            class="ffun-normal-link"
            :href="settings.githubRepo"
            target="_blank"
            >Open source</a
          >, self-hosted.</li
        >
        <li>No black box recommendation algorithms.</li>
        <li>No "smart" reordering.</li>
        <li>No ads.</li>
        <li>No selling of your data.</li>
      </ul>

      <h2>How it looks like</h2>
    </div>

    <img
      class="border-2 rounded border-slate-300"
      src="/news-filtering-example.png"
      alt="News filtering example" />
  </wide-layout>
</template>

<script lang="ts" setup>
  import * as settings from "@/logic/settings";
</script>
