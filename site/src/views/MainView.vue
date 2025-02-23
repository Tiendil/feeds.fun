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

      <div class="max-w-3xl flex mx-auto justify-center items-center my-4">
        <div class="w-1/2 h-32 bg-blue-200 rounded-l-md">
          <i class="ti ti-number-1"></i> Subscribe to news feeds
        </div>
        <div class="w-1/2 h-32 bg-slate-200 rounded-r-md">
          All major content providers as well the most private blogs support delivering news feeds. You can subscribe to the sites like Reddit, ArXiv.org, Medium, as well as to the blogs of your friends and access all the news in one place.
        </div>
      </div>

      <div class="max-w-3xl flex mx-auto justify-center items-center my-4">
        <div class="w-1/2 h-32 bg-blue-200 rounded-l-md">
          <i class="ti ti-number-2"></i> Feeds Fun tags every news article
        </div>
        <div class="w-1/2 h-32 bg-slate-200 rounded-r-md">
          Feeds Fun automatically assigns tags to every news article, according to its content. Tags will represent people, places, topics, games, etc.
        </div>
      </div>

      <div class="max-w-3xl flex mx-auto justify-center items-center my-4">
        <div class="w-1/2 h-32 bg-blue-200 rounded-l-md">
          <i class="ti ti-number-3"></i> Create rules to score news
        </div>
        <div class="w-1/2 h-32 bg-slate-200 rounded-r-md">
          You can create rules to score news based on tags. For example, you can create a rule to score news with the "Python" tag higher than news with the "Java" tag. Or to exclude all news with the "Politics" tag.
        </div>
      </div>

      <div class="max-w-3xl flex mx-auto justify-center items-center my-4">
        <div class="w-1/2 h-32 bg-blue-200 rounded-l-md">
          <i class="ti ti-number-4"></i>Read only news that matters to you
        </div>
        <div class="w-1/2 h-32 bg-slate-200 rounded-r-md">
          Feeds Fun will sort and filter news according to your rules. The most important news for your will be always on top.
        </div>
      </div>

      <div class="max-w-3xl flex mx-auto justify-center items-center my-4">
        <div class="w-1/2 h-32 bg-blue-200 rounded-l-md">
          <i class="ti ti-number-5"></i>Do not loose transparency
        </div>
        <div class="w-1/2 h-32 bg-slate-200 rounded-r-md">
          Since we use straightforward approach to scoring news, you can always check how your rules affect the news order, which news has lower score and why. No magic, no black boxes, your news are totally under your control. Don't trust by words? Check our <external-url url="https://github.com/Tiendil/feeds.fun" text="source code"/>.
        </div>
      </div>

      <div class="max-w-5xl mx-auto flex flex-wrap justify-center gap-6 lg:gap-8">
        <div class="bg-slate-100 p-6 rounded-md w-72 text-left">
        <h3 class="text-lg font-bold mb-2">Smart Tagging</h3>
        <p class="text-sm">
          Automatically assigns relevant tags to news articles for better
          organization.
        </p>
      </div>
      <div class="bg-slate-100 p-6 rounded-md w-72 text-left">
        <h3 class="text-lg font-bold mb-2">Custom Scoring</h3>
        <p class="text-sm">
          Create rules to score news based on your preferred tags and topics.
        </p>
      </div>
      <div class="bg-slate-100 p-6 rounded-md w-72 text-left">
        <h3 class="text-lg font-bold mb-2">Filtered Feed</h3>
        <p class="text-sm">
          Sort and filter news so you only read the most important stories.
        </p>
      </div>
      <div class="bg-slate-100 p-6 rounded-md w-72 text-left">
        <h3 class="text-lg font-bold mb-2">Curated Collections</h3>
        <p class="text-sm">
          Explore handpicked thematic collections of feeds for quick insights.
        </p>
      </div>
      <div class="bg-slate-100 p-6 rounded-md w-72 text-left">
        <h3 class="text-lg font-bold mb-2">Transparent &amp; Open</h3>
        <p class="text-sm">
          Open source, self-hosted – no hidden algorithms or ads.
        </p>
      </div>
    </div>

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
